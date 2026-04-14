from __future__ import annotations

import threading
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .db import db
from .models import Project, ScheduledTask, ScheduledTaskRun, TimelineEvent


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _create_timeline_event(
    project_id: int, event_type: str, payload: dict
) -> TimelineEvent:
    event = TimelineEvent(
        project_id=project_id,
        event_type=event_type,
        payload_json=json.dumps(payload, ensure_ascii=True),
        created_at=_utc_now(),
    )
    db.session.add(event)
    return event


class TaskScheduler:
    def __init__(
        self,
        app,
        opencode_client,
        poll_interval_seconds: int = 20,
        task_run_retention_days: int = 30,
    ):
        self._app = app
        self._opencode_client = opencode_client
        self._poll_interval_seconds = max(5, poll_interval_seconds)
        self._task_run_retention_days = max(1, task_run_retention_days)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_prune_at: datetime | None = None
        self._last_pruned_count = 0
        self._last_loop_at: datetime | None = None
        self._last_loop_error: str | None = None
        self._status_lock = threading.Lock()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._recover_interrupted_runs()
        self._thread = threading.Thread(
            target=self._loop, name="task-scheduler", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)

    def trigger_task_now(self, task_id: int) -> int:
        with self._app.app_context():
            task = ScheduledTask.query.get(task_id)
            if task is None:
                raise ValueError("Scheduled task not found")

            run = ScheduledTaskRun(
                task_id=task.id,
                project_id=task.project_id,
                status="running",
                trigger="manual",
                started_at=_utc_now(),
            )
            task.last_status = "running"
            task.last_error = None
            db.session.add(run)
            db.session.commit()

            self._execute_run(task_id=task.id, run_id=run.id)
            return run.id

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._run_due_tasks_once()
                self._prune_old_task_runs_if_due()
                with self._status_lock:
                    self._last_loop_at = _utc_now()
                    self._last_loop_error = None
            except Exception:
                with self._status_lock:
                    self._last_loop_at = _utc_now()
                    self._last_loop_error = "scheduler_loop_error"
            self._stop_event.wait(self._poll_interval_seconds)

    def _prune_old_task_runs_if_due(self) -> None:
        now = _utc_now()
        if self._last_prune_at is not None:
            last = _ensure_utc(self._last_prune_at) or now
            if (now - last) < timedelta(hours=1):
                return

        cutoff = now - timedelta(days=self._task_run_retention_days)
        deleted_count = 0
        with self._app.app_context():
            deleted_count = ScheduledTaskRun.query.filter(
                ScheduledTaskRun.finished_at.isnot(None),
                ScheduledTaskRun.finished_at < cutoff,
            ).delete(synchronize_session=False)
            db.session.commit()

        with self._status_lock:
            self._last_prune_at = now
            self._last_pruned_count = int(deleted_count or 0)

    def get_status(self) -> dict:
        with self._status_lock:
            last_loop_at = self._last_loop_at
            last_prune_at = self._last_prune_at
            last_loop_error = self._last_loop_error
            last_pruned_count = self._last_pruned_count

        is_running = bool(self._thread and self._thread.is_alive())
        return {
            "running": is_running,
            "pollIntervalSeconds": self._poll_interval_seconds,
            "taskRunRetentionDays": self._task_run_retention_days,
            "lastLoopAt": last_loop_at.isoformat() if last_loop_at else None,
            "lastLoopError": last_loop_error,
            "lastPruneAt": last_prune_at.isoformat() if last_prune_at else None,
            "lastPrunedCount": last_pruned_count,
        }

    def _recover_interrupted_runs(self) -> None:
        with self._app.app_context():
            interrupted = ScheduledTaskRun.query.filter_by(status="running").all()
            if not interrupted:
                return

            now = _utc_now()
            affected_task_ids: set[int] = set()
            for run in interrupted:
                run.status = "interrupted"
                run.finished_at = now
                run.error = "Scheduler restart detected before task run finished"
                affected_task_ids.add(run.task_id)
                _create_timeline_event(
                    project_id=run.project_id,
                    event_type="scheduled_task_run",
                    payload={
                        "taskRunId": run.id,
                        "status": "interrupted",
                        "trigger": run.trigger,
                        "sessionId": run.session_id,
                        "heartbeatLoaded": bool(run.heartbeat_loaded),
                        "startedAt": run.started_at.isoformat()
                        if run.started_at
                        else None,
                        "finishedAt": run.finished_at.isoformat()
                        if run.finished_at
                        else None,
                        "error": run.error,
                        "outputPreview": run.output_preview,
                    },
                )

            for task_id in affected_task_ids:
                task = ScheduledTask.query.get(task_id)
                if task is None:
                    continue
                task.last_status = "interrupted"
                task.last_error = "Last run interrupted by scheduler restart"
                task.next_run_at = now + timedelta(minutes=task.interval_minutes)

            db.session.commit()

    def _run_due_tasks_once(self) -> None:
        with self._app.app_context():
            now = _utc_now()
            due_tasks = (
                ScheduledTask.query.filter(
                    ScheduledTask.enabled.is_(True),
                    ScheduledTask.next_run_at.isnot(None),
                    ScheduledTask.next_run_at <= now,
                )
                .order_by(ScheduledTask.next_run_at.asc())
                .limit(10)
                .all()
            )

            run_queue: list[tuple[int, int]] = []
            for task in due_tasks:
                run = ScheduledTaskRun(
                    task_id=task.id,
                    project_id=task.project_id,
                    status="running",
                    trigger="schedule",
                    started_at=now,
                )
                task.last_status = "running"
                task.last_error = None
                task.next_run_at = now + timedelta(minutes=task.interval_minutes)
                db.session.add(run)
                db.session.flush()
                run_queue.append((task.id, run.id))

            db.session.commit()

        for task_id, run_id in run_queue:
            self._execute_run(task_id=task_id, run_id=run_id)

    def _execute_run(self, task_id: int, run_id: int) -> None:
        with self._app.app_context():
            task = ScheduledTask.query.get(task_id)
            run = ScheduledTaskRun.query.get(run_id)
            if task is None or run is None:
                return

            project = Project.query.get(task.project_id)
            if project is None:
                run.status = "failed"
                run.finished_at = _utc_now()
                run.error = "Project not found"
                _create_timeline_event(
                    project_id=run.project_id,
                    event_type="scheduled_task_run",
                    payload={
                        "taskRunId": run.id,
                        "status": run.status,
                        "trigger": run.trigger,
                        "sessionId": run.session_id,
                        "heartbeatLoaded": bool(run.heartbeat_loaded),
                        "startedAt": run.started_at.isoformat()
                        if run.started_at
                        else None,
                        "finishedAt": run.finished_at.isoformat()
                        if run.finished_at
                        else None,
                        "error": run.error,
                        "outputPreview": run.output_preview,
                    },
                )
                db.session.commit()
                return

            now = _utc_now()
            run.started_at = _ensure_utc(run.started_at) or now
            task.last_run_at = now
            task.last_status = "running"
            task.last_error = None
            db.session.commit()

        task_session_id: str | None = None
        try:
            heartbeat_path = Path(project.path) / "heartbeat_instruction.md"
            if not heartbeat_path.exists():
                raise FileNotFoundError(
                    f"Missing heartbeat_instruction.md in project directory: {project.path}"
                )

            heartbeat_text = heartbeat_path.read_text(encoding="utf-8").strip()
            if not heartbeat_text:
                raise ValueError("heartbeat_instruction.md is empty")

            session = self._opencode_client.create_session(
                directory=project.path,
                title=f"{project.name} scheduled task",
            )
            task_session_id = str(session.get("id") or "")
            if not task_session_id:
                raise ValueError("Could not create task session")

            self._opencode_client.send_message(
                session_id=task_session_id,
                directory=project.path,
                text=(
                    "Read and apply the following heartbeat instruction before any further steps:\n\n"
                    + heartbeat_text
                ),
            )

            response = self._opencode_client.send_message(
                session_id=task_session_id,
                directory=project.path,
                text=task.instruction,
            )
            parts = response.get("parts") if isinstance(response, dict) else []
            preview = ""
            if isinstance(parts, list):
                text_chunks: list[str] = []
                for part in parts:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_value = part.get("text")
                        if isinstance(text_value, str):
                            text_chunks.append(text_value)
                preview = "\n".join(text_chunks).strip()[:1200]

            with self._app.app_context():
                task = ScheduledTask.query.get(task_id)
                run = ScheduledTaskRun.query.get(run_id)
                if task is None or run is None:
                    return
                run.status = "completed"
                run.finished_at = _utc_now()
                run.session_id = task_session_id
                run.heartbeat_loaded = True
                run.output_preview = preview
                task.last_status = "completed"
                task.last_error = None
                _create_timeline_event(
                    project_id=task.project_id,
                    event_type="scheduled_task_run",
                    payload={
                        "taskRunId": run.id,
                        "status": run.status,
                        "trigger": run.trigger,
                        "sessionId": run.session_id,
                        "heartbeatLoaded": bool(run.heartbeat_loaded),
                        "startedAt": run.started_at.isoformat()
                        if run.started_at
                        else None,
                        "finishedAt": run.finished_at.isoformat()
                        if run.finished_at
                        else None,
                        "error": run.error,
                        "outputPreview": run.output_preview,
                    },
                )
                db.session.commit()
        except Exception as exc:
            with self._app.app_context():
                task = ScheduledTask.query.get(task_id)
                run = ScheduledTaskRun.query.get(run_id)
                if task is None or run is None:
                    return
                run.status = "failed"
                run.finished_at = _utc_now()
                run.session_id = task_session_id
                run.error = str(exc)
                task.last_status = "failed"
                task.last_error = str(exc)
                _create_timeline_event(
                    project_id=task.project_id,
                    event_type="scheduled_task_run",
                    payload={
                        "taskRunId": run.id,
                        "status": run.status,
                        "trigger": run.trigger,
                        "sessionId": run.session_id,
                        "heartbeatLoaded": bool(run.heartbeat_loaded),
                        "startedAt": run.started_at.isoformat()
                        if run.started_at
                        else None,
                        "finishedAt": run.finished_at.isoformat()
                        if run.finished_at
                        else None,
                        "error": run.error,
                        "outputPreview": run.output_preview,
                    },
                )
                db.session.commit()
        finally:
            if task_session_id:
                try:
                    self._opencode_client.delete_session(task_session_id)
                except Exception:
                    pass

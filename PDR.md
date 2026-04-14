
# Product Requirements Document (PRD): OpenCode Web Controller

## 1. Product Vision

Build a mobile-first, Telegram-like PWA that controls local OpenCode sessions on Linux without losing technical depth. The interface must clearly show thinking, intermediate steps, tool output, approvals, and file changes, while keeping long outputs readable through collapsible message blocks.

The app is a single-user control surface: one owner, one password, no team collaboration.

## 2. Goals and Non-Goals

### 2.1 Goals

* Deliver a full app (not an MVP) that is usable daily on mobile and desktop.
* Preserve OpenCode transparency: show intermediate reasoning-style progress, terminal logs, and step-by-step execution states.
* Provide a project-centric chat model where each project is a chat and has one active interactive session.
* Support up to 10 concurrently running project sessions, with up to 1000 total stored projects/chats.
* Include built-in STT/TTS with OpenAI-compatible local endpoints.
* Include one scheduled task per project using `heartbeat_instruction.md`, executed in a dedicated task session.

### 2.2 Non-Goals

* Multi-user support.
* Human-to-human chat.
* Multiple interactive sessions per project.
* More than one scheduled task per project.
* Cross-platform host support beyond Linux.
* Real-time voice/video calling UI (this app uses STT/TTS only).

## 3. Target User and Core Model

### 3.1 User Model

* Exactly one user account protected by one password.
* Session-based authentication is sufficient.

### 3.2 Domain Model

* **Project (Chat):** maps to a filesystem folder.
* **Interactive Session:** one per project, used for normal chat-driven OpenCode work.
* **Task Session:** separate dedicated session for scheduled task execution only.
* **Message/Event Timeline:** immutable log of prompts, responses, streamed events, approvals, and artifacts.

## 4. Functional Requirements

### 4.1 Chat and Session Management

* User can create/import projects by selecting a local folder path.
* Each project has exactly one interactive session.
* On opening the app, last used project and its session are auto-selected.
* Project list is sorted by recent activity (most recent first).
* System supports 1000 stored projects/chats and 10 concurrently running sessions.

### 4.2 OpenCode Interaction

* Real-time streaming via WebSocket/SSE for:
  * incremental assistant output,
  * intermediate steps/status transitions,
  * tool execution updates,
  * terminal/stdout/stderr logs.
* User can send prompts and slash commands from chat input.
* Required command support at minimum:
  * `/models`
  * `/agent`
  * `/clear`
* Additional commonly used OpenCode actions must be exposed via command menu or UI controls where relevant (for example, model switch, context clear, session restart, stop generation).

### 4.3 Message Rendering and Readability

* Messages support markdown and code highlighting.
* Long technical payloads are collapsible/expandable with a clear summary row:
  * file changes,
  * long tool outputs,
  * verbose intermediate logs,
  * stack traces.
* File change blocks should show compact metadata first (file path, change type, rough diff size), with full content on expand.
* Thinking/progress/intermediate steps must be visibly separated from final response text.

### 4.4 Approval Flow

* Any OpenCode approval prompt is presented to the user with binary actions only (approve/deny).
* Input area behavior adapts when an approval is pending (prevent ambiguous free-text where needed).
* Approval decision is logged in the timeline with timestamp.

### 4.5 Scheduled Task (Per Project)

* Each project can define exactly one scheduled task configuration.
* Task execution always starts in a dedicated task session (not the interactive session).
* At task start, the agent must automatically read `heartbeat_instruction.md` for that project before proceeding.
* Task run logs, outputs, and failures are persisted and visible in the chat timeline.

### 4.6 Voice Features (Required)

* Microphone button in composer records audio and sends to STT endpoint.
* STT transcript is inserted into input box for review/edit before send.
* TTS can play assistant messages with play/stop controls.
* Use the following runtime configuration:

```env
TTS_BASE_URL="http://127.0.0.1:8969/v1"
TTS_MODEL="speaches-ai/Kokoro-82M-v1.0-ONNX"
TTS_VOICE="af_alloy"
TTS_API_KEY="not-required"

STT_BASE_URL="http://127.0.0.1:8969/v1"
STT_MODEL="Systran/faster-whisper-medium.en"
STT_API_KEY="not-required"
```

## 5. UI/UX Requirements (Telegram-like)

### 5.1 Layout

* Mobile-first responsive design with Telegram Web interaction patterns.
* Mobile: project list in drawer/sheet from left.
* Desktop: persistent left sidebar for project list + main conversation pane.
* Bottom-pinned input composer with slash-command autocomplete and mic button.

### 5.2 Conversation Experience

* User messages right-aligned; assistant/system/tool messages left-aligned.
* Distinct visual treatment for:
  * final answers,
  * intermediate steps,
  * tool output,
  * approvals,
  * file changes.
* Smooth streaming updates with no major layout jumps while content grows.

### 5.3 PWA Behavior

* Installable PWA on mobile and desktop browsers.
* App shell loads even under weak connectivity; live session features degrade gracefully when offline.
* Push notifications are optional; not required for initial launch.

### 5.4 Telegram Web Fidelity Details

The following interaction patterns are required to keep a Telegram-like feel while staying aligned with OpenCode workflow.

* **Sidebar behavior**
  * Desktop sidebar is resizable and persists width in local storage.
  * Sidebar width constraints should be enforced (recommended baseline: min `256px`, default around `420px`, capped by viewport).
  * Mobile chat navigation uses route-aware back behavior and drawer/pane transitions.
* **Header and chrome rhythm**
  * Chat header height target: `56px` with avatar, title/subtitle, and action buttons.
  * Composer and list spacing should keep a dense Telegram-like information layout, not a large-card chat UI.
* **Message list ergonomics**
  * Sticky date separators for long timelines.
  * Empty-chat state with centered compact hint card.
  * Unread boundary marker support (when historical unread state exists).
  * Smart auto-scroll: move to unread boundary first, otherwise to latest message.
* **Message bubble language**
  * Separate visual style for own vs assistant/system messages.
  * Bubble grouping by adjacency (top/middle/bottom/single radius variants).
  * Per-message metadata row supports timestamp + delivery/state badges.
* **Composer behavior**
  * Emoji picker, attachment button, and send action in Telegram-like arrangement.
  * Enter sends message; Shift+Enter inserts newline.
  * Rich text is optional; markdown-first input is required.
  * Attachment preview chips must be removable before send.
* **Mobile-first quality bar**
  * Preserve usability at narrow widths without hiding core controls.
  * Avoid layout shifts while streaming; content growth should feel stable.

## 6. Performance and Reliability Requirements

* Time to interactive on warm load: <= 2.5s on modern mobile device over Wi-Fi.
* Streaming latency target from backend event to UI paint: <= 400ms median.
* Chat list render with 1000 projects: <= 1s with virtualization.
* Reconnect behavior after transient network loss:
  * auto-reconnect within 5s,
  * restore active project/session context,
  * backfill missed events when supported.
* Scheduled task execution must survive browser closure (server-side scheduler).

## 7. Security and Access

* Single-password authentication and secure session cookies.
* LAN/Tailscale-oriented deployment; no mandatory public exposure.
* Security hardening focus is practical (single trusted user model), not enterprise RBAC.

## 8. Technical Constraints and Stack Direction

* Host OS: Linux only.
* Backend: Python + Flask (+ WebSocket support).
* Frontend: React or Vue with a mobile-first component architecture.
* Storage: persistent DB for projects, messages, session metadata, scheduled tasks.
* Deployment: Docker Compose recommended for app + DB + supporting services.

### 8.1 OpenCode Server Integration (Source of Truth)

* The app must use `opencode serve` HTTP API as the primary execution backend.
* Default server endpoint: `http://127.0.0.1:4096`.
* Server startup contract:
  * `opencode serve --hostname 127.0.0.1 --port 4096 --cors <web-origin>`
  * Health check: `GET /global/health` must return `healthy=true` before UI enables prompts.
* Optional upstream auth:
  * If OpenCode server basic auth is enabled (`OPENCODE_SERVER_USERNAME`/`OPENCODE_SERVER_PASSWORD`), backend must attach `Authorization: Basic ...` for all upstream calls.

### 8.2 Required OpenCode API Endpoints

The backend must implement a stable adapter over the following OpenCode endpoints so frontend contracts remain consistent even if OpenCode evolves.

* **Connectivity and discovery**
  * `GET /global/health`
  * `GET /doc` (for compatibility checks and debugging)
* **Project and sessions**
  * `GET /project`
  * `GET /session`
  * `POST /session`
  * `PATCH /session/:id`
  * `DELETE /session/:id`
  * `POST /session/:id/abort`
  * `GET /session/status`
* **Messages and commands**
  * `GET /session/:id/message`
  * `POST /session/:id/message`
  * `POST /session/:id/prompt_async`
  * `POST /session/:id/command`
  * `POST /session/:id/shell` (optional UI surface, backend-ready)
* **Approvals and diffs**
  * `POST /session/:id/permissions/:permissionID`
  * `GET /session/:id/diff`
* **Streaming**
  * `GET /event` (SSE)

### 8.3 Backend Gateway Responsibilities

The Flask backend is not just a proxy; it is a stateful gateway that normalizes OpenCode behavior for a mobile UI.

* Maintain app auth/session state (single-password local login).
* Keep mapping: `project_id -> opencode_session_id` for the one interactive session per project rule.
* Subscribe to OpenCode SSE and fan out normalized events to browser sockets.
* Persist timeline events in DB so app can restore full history on reconnect/reload.
* Convert OpenCode permission events into binary approve/deny UI actions.
* Provide backpressure/throttling for high-frequency streaming tokens to avoid UI jank.

### 8.4 Event Pipeline and Reliability (Based on Bot Patterns)

To match production behavior proven in `opencode-telegram-bot`, implement these patterns:

* SSE listener with exponential reconnect backoff (start ~1s, cap ~15s).
* Abort controller per active stream so project switches can cancel stale listeners immediately.
* Non-blocking event processing (`queue + async dispatch`) to prevent head-of-line blocking during bursts.
* Streaming chunk throttling before forwarding to client (target ~200-500ms update cadence).
* On reconnect, reload latest session messages and diffs to close event gaps.

### 8.5 Command Mapping

Slash command UX in the web composer maps to OpenCode operations:

* `/models` -> provider/model list + `PATCH /config` update (or equivalent model-switch command path).
* `/agent` -> switch active agent for next prompts.
* `/clear` -> clear context via OpenCode command endpoint.
* `stop` action in UI -> `POST /session/:id/abort`.

### 8.6 Scheduled Task Technical Flow

Each project has exactly one scheduled task and uses a dedicated task session per run.

* Scheduler runs server-side (independent from browser lifecycle).
* For each execution:
  * create a temporary OpenCode session in that project,
  * inject and run `heartbeat_instruction.md` first,
  * execute scheduled instruction,
  * persist full output/status,
  * close/delete temporary task session if configured to keep storage compact.
* Cron frequency guardrail: reject schedules more frequent than every 5 minutes.
* If app restarts while task is `running`, mark last run as interrupted and reschedule safely.

### 8.7 STT/TTS Backend Endpoints

Backend provides stable media endpoints for the frontend and isolates provider differences.

* `POST /api/stt/transcribe`
  * accepts recorded audio,
  * calls `${STT_BASE_URL}/audio/transcriptions`,
  * returns plain transcript text plus metadata.
* `POST /api/tts/speak`
  * accepts response text,
  * calls `${TTS_BASE_URL}/audio/speech`,
  * returns streamable audio bytes/URL.
* Failures in STT/TTS must never block normal text chat.

## 9. Data and Persistence Requirements

* Persist all chats/messages/events indefinitely by default.
* Sort project list by most recently active chat.
* Persist:
  * project metadata (path, title, timestamps),
  * interactive session metadata,
  * task session metadata,
  * message/event timeline,
  * approvals and outcomes,
  * scheduled task config and run history.

## 10. Acceptance Criteria

* User can manage at least 1000 project chats; UI remains responsive.
* User can run up to 10 concurrent interactive project sessions.
* Opening app restores the last used project/session automatically.
* Long outputs and file changes are collapsible and readable on mobile.
* Intermediate steps and tool logs are visible in real time without losing context.
* Approval prompts are handled through binary UI actions and recorded.
* One scheduled task per project runs in a dedicated task session and auto-reads `heartbeat_instruction.md`.
* STT and TTS both function via configured OpenAI-compatible endpoints.
* App is installable as a PWA and works on mobile and desktop browsers.

## 11. Open Implementation Decisions (To Finalize During Build)

* Frontend framework final choice: React vs Vue.
* Exact scheduler implementation: APScheduler vs Celery.
* Message event schema for representing intermediate steps and collapsible sections.
* Whether to support optional push notifications in first production release.

## 12. Reference Implementation Notes

Technical details in this PRD align with:

* OpenCode Server API documentation (`/docs/server`), including sessions, messages, commands, permissions, and SSE events.
* Patterns observed in `grinev/opencode-telegram-bot`, especially:
  * SSE subscription lifecycle with reconnect handling,
  * scheduled task runtime design (dedicated temporary session per run),
  * natural-language schedule parsing through OpenCode prompt + strict JSON validation,
  * streaming/throttling and interaction flow control for approvals.
* Telegram clone UI patterns summarized from TropicolX's 3-part Telegram Web clone series (layout rhythm, sidebar behavior, custom list/composer/message ergonomics).

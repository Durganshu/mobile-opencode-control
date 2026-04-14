# OpenCode Web Controller - UI Spec

This UI spec translates `PDR.md` and `tasks.md` into implementation-ready frontend component contracts.

Scope notes:

- Single user only.
- One interactive session per project.
- One scheduled task per project.
- Telegram-like visual/interaction behavior.
- No voice/video calling UI beyond STT/TTS controls in composer/messages.

---

## 1) Global App Shell

## Component: `AppShell`

Purpose: top-level responsive shell with sidebar + conversation pane + auth gate.

### Props

- `isAuthenticated: boolean`
- `activeProjectId: string | null`
- `onProjectSelect: (projectId: string) => void`
- `children: React.ReactNode`

### State

- `isMobileDrawerOpen: boolean`
- `sidebarWidth: number` (persisted to `localStorage` key: `sidebarWidth`)

### Behavior

- Desktop: persistent left sidebar, resizable via drag handle.
- Mobile: drawer/sheet sidebar; active chat pane fills screen.
- Width constraints:
  - `min: 256px`
  - `default: 420px`
  - `max: dynamic by viewport` (recommended cap around 33-40% of width on large screens).
- Restore `sidebarWidth` on load.

### Events

- `sidebar.width.changed`
- `sidebar.drawer.opened`
- `sidebar.drawer.closed`

---

## 2) Sidebar and Project List

## Component: `Sidebar`

Purpose: show recent project chats, search, and quick navigation.

### Props

- `projects: ProjectListItem[]`
- `activeProjectId: string | null`
- `loading: boolean`
- `onSelectProject: (projectId: string) => void`
- `onCreateProject: () => void`
- `onSearch: (query: string) => void`
- `width: number`
- `onWidthChange: (width: number) => void`

### `ProjectListItem`

- `id: string`
- `name: string`
- `path: string`
- `lastMessagePreview: string | null`
- `lastActivityAt: string`
- `unreadCount?: number`
- `sessionStatus: "idle" | "running" | "waiting_approval" | "error"`
- `hasScheduledTask: boolean`

### Behavior

- Sorted by `lastActivityAt DESC`.
- Virtualized list for large datasets.
- Active item highlights.
- Shows unread badge when `unreadCount > 0`.
- Search filters by project name/path.

### Validation Targets

- Smooth scrolling and selection with 1000 projects.
- Keyboard focus support for navigation list items.

---

## 3) Chat Header

## Component: `ChatHeader`

Purpose: fixed top bar for active project context and actions.

### Props

- `project: ActiveProject`
- `sessionStatus: "idle" | "running" | "waiting_approval" | "error"`
- `onBackMobile: () => void`
- `onOpenCommandMenu: () => void`
- `onAbort: () => void`
- `onOpenProjectSettings: () => void`

### `ActiveProject`

- `id: string`
- `name: string`
- `path: string`
- `sessionId: string`

### Behavior

- Height target: `56px`.
- Desktop: no back button.
- Mobile: back button appears and returns to sidebar list.
- Abort button disabled unless session is running.

---

## 4) Message Timeline

## Component: `MessageTimeline`

Purpose: render all timeline items with streaming updates and stable scroll behavior.

### Props

- `items: TimelineItem[]`
- `loading: boolean`
- `hasUnreadBoundary: boolean`
- `unreadBoundaryItemId?: string`
- `onLoadOlder: () => Promise<void>`

### `TimelineItem`

- `id: string`
- `projectId: string`
- `sessionId: string`
- `createdAt: string`
- `role: "user" | "assistant" | "system" | "tool"`
- `kind:`
  - `"user_prompt"`
  - `"assistant_final"`
  - `"assistant_intermediate"`
  - `"tool_event"`
  - `"approval_request"`
  - `"approval_decision"`
  - `"file_diff"`
  - `"scheduled_task_event"`
- `status?: "streaming" | "complete" | "error"`
- `content: string`
- `meta?: Record<string, unknown>`

### Behavior

- Sticky date separators.
- Empty-state card when no messages.
- Streaming chunks append in-place without layout jumps.
- Auto-scroll rules:
  - if unread boundary exists: first scroll to boundary;
  - else keep near latest during active stream (do not yank user if manually scrolled away).

---

## 5) Message Bubble

## Component: `MessageBubble`

Purpose: Telegram-like bubble rendering for each timeline item.

### Props

- `item: TimelineItem`
- `isOwn: boolean`
- `groupPosition: "single" | "top" | "middle" | "bottom"`
- `onExpandSection?: (itemId: string, sectionId: string) => void`
- `onCollapseSection?: (itemId: string, sectionId: string) => void`

### Behavior

- Left/right alignment by `role` (user on right, others left).
- Group radius changes by `groupPosition`.
- Metadata row always available (time + status badge).
- Markdown rendering for content; syntax highlighting for fenced code.

### Variants

- `assistant_final`: regular answer bubble.
- `assistant_intermediate`: subdued/progress style.
- `tool_event`: monospaced/log style.
- `file_diff`: collapsible diff summary + details.
- `scheduled_task_event`: task badge + result/status.

---

## 6) Collapsible Technical Blocks

## Component: `CollapsibleBlock`

Purpose: keep long technical output readable.

### Props

- `id: string`
- `title: string`
- `subtitle?: string`
- `defaultOpen?: boolean`
- `sizeHint?: string` (example: `"2.1 KB"`)
- `children: React.ReactNode`

### Required Use Cases

- File diffs (path, operation, rough size).
- Long tool logs.
- Stack traces.
- Verbose intermediate reasoning/progress chunks.

### Behavior

- Stable expand/collapse animation (no page jump).
- Remember per-item open state while current chat is mounted.

---

## 7) Approval Card

## Component: `ApprovalCard`

Purpose: explicit binary approval flow for OpenCode permission events.

### Props

- `permissionId: string`
- `title: string`
- `details: string`
- `pending: boolean`
- `onApprove: (permissionId: string) => Promise<void>`
- `onDeny: (permissionId: string) => Promise<void>`

### Behavior

- Only two actions: Approve / Deny.
- While pending decision exists, composer input can be disabled or constrained.
- Decision result should render as timeline event with timestamp.

---

## 8) Composer

## Component: `Composer`

Purpose: send prompt/commands, attach files, and use STT.

### Props

- `disabled: boolean`
- `placeholder?: string`
- `pendingApproval: boolean`
- `onSubmitPrompt: (payload: PromptPayload) => Promise<void>`
- `onRunCommand: (command: string, args?: string[]) => Promise<void>`
- `onStartRecording: () => void`
- `onStopRecording: () => Promise<void>`
- `onAttachFiles: (files: File[]) => void`

### `PromptPayload`

- `text: string`
- `attachments?: AttachmentRef[]`

### Behavior

- Enter submits, Shift+Enter newline.
- Slash menu opens when input starts with `/`.
- STT transcript inserts into input for review/edit before submit.
- Attachment chips appear above input and are removable before send.

### Commands (required)

- `/models`
- `/agent`
- `/clear`

---

## 9) Command Palette

## Component: `CommandMenu`

Purpose: Telegram-like command autocomplete near composer.

### Props

- `open: boolean`
- `query: string`
- `commands: CommandItem[]`
- `onSelect: (cmd: CommandItem) => void`

### `CommandItem`

- `id: string`
- `name: string` (example: `/models`)
- `description: string`
- `argsSchema?: Record<string, unknown>`

### Behavior

- Keyboard navigation (up/down/enter/escape).
- Filters by prefix and fuzzy text.

---

## 10) Scheduled Task UI

## Component: `ProjectTaskPanel`

Purpose: configure and inspect one scheduled task per project.

### Props

- `projectId: string`
- `task: ProjectTask | null`
- `onCreateTask: (input: TaskInput) => Promise<void>`
- `onUpdateTask: (taskId: string, patch: Partial<TaskInput>) => Promise<void>`
- `onDeleteTask: (taskId: string) => Promise<void>`

### `ProjectTask`

- `id: string`
- `projectId: string`
- `scheduleText: string`
- `scheduleSummary: string`
- `nextRunAt: string | null`
- `lastRunAt: string | null`
- `lastStatus: "idle" | "running" | "success" | "error"`
- `lastError: string | null`

### `TaskInput`

- `scheduleText: string`
- `instruction: string`

### Behavior

- Enforce one task per project in UI and API.
- Show run history snippets in timeline.
- Validate frequency guardrail (`>= 5 minutes` for recurring schedules).

---

## 11) Voice UX

## Component: `VoiceControls`

Purpose: STT capture and TTS playback control.

### Props

- `onTranscribe: (audio: Blob) => Promise<string>`
- `onSpeak: (text: string) => Promise<void>`
- `onStopSpeak: () => void`

### Behavior

- Recorder status states: `idle | recording | processing | error`.
- Transcribed text inserted in composer, never auto-sent.
- TTS controls live on assistant final messages.
- STT/TTS failure shows non-blocking error toast.

---

## 12) Frontend Event Model

Use a normalized event bus in the client so streaming and persistence behave consistently.

## Event Types

- `session.stream.started`
- `session.stream.chunk`
- `session.stream.completed`
- `session.stream.error`
- `session.permission.requested`
- `session.permission.resolved`
- `session.diff.available`
- `task.run.started`
- `task.run.completed`
- `task.run.failed`

## Required Guarantees

- Event handling must be idempotent by `(event_id)`.
- UI rendering uses stable keys by timeline item id.
- Chunk coalescing/throttle window target: `200-500ms`.

---

## 13) Accessibility + Interaction Quality

- Focus rings visible on keyboard navigation.
- ARIA labels on icon-only buttons (send, attach, mic, abort, approve/deny).
- Color contrast must meet WCAG AA for text and controls.
- Touch targets at least `40x40px` on mobile controls.

---

## 14) Done Criteria for UI Layer

UI layer is considered complete when:

- Core components above are implemented and wired to backend contracts.
- Telegram-like behavior is visible across mobile and desktop.
- Streaming, approvals, diffs, and tasks are all represented in one coherent timeline.
- Sidebar width persistence and mobile navigation are stable.
- STT/TTS controls are usable and non-blocking.

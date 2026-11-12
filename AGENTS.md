# AGENTS.md

## Code style

- Comments: 5-15 words max. No docstrings. Comment only non-obvious "why".
- No inline styles. Move declarations into `interfaces/frontend/src/index.css`
  under `@layer components`, keyed on the element's existing `aui-*` or `app-*` class.
- Runtime-computed values (scroll masks, progress widths) stay inline, but only
  as a CSS custom property. The consuming declaration lives in `index.css`.
- No underscore-prefixed identifiers.
- All code edits must be kept minimal to ensure the smallest possible fix or implementation
  of features

## Code flow

`execution.py web` supervises three processes:

| Process | Command | Port |
| --- | --- | --- |
| LangGraph API | `langgraph dev --host 127.0.0.1 --port 2024 --no-browser` | 2024 |
| Ingest API | `python -m interfaces.ingest` | 2030 |
| Vite | `npm run dev -- --host 127.0.0.1 --port 5173 --strictPort` | 5173 |

Each port is probed before launch; a listening port is reused, not restarted.

### Agent core

`langgraph.json` serves one graph, `agent` -> `./agent/agent.py:stack_agent`,
which is `deep_agent.build`: a lazy coroutine singleton opening an
`AsyncSqliteSaver` and `AsyncSqliteStore` on `database/database.db`.

`construct_agent` builds a deep agent with a `CompositeBackend`
(`/longtermmemories/` -> store, `/project/` -> `~/.Charles/project`), model
set in `providers.json` under `/project/` path, and subagents. Nodes are `model`, `tools`, plus one per
lifecycle hook override: `PatchToolCallsMiddleware.before_agent`,
`MemoryMiddleware.before_agent`, `TodoListMiddleware.after_model`.

### Send path

`chat-runtime.tsx` builds the runtime, `onNew` -> `client.runs.stream` ->
`POST /threads/{id}/runs/stream` over SSE. Stream modes are
`["messages","updates","custom"]`. `streamSubgraphs` is never set, so no
`messages|<namespace>` events are emitted.

### Stream path

SSE event types: `messages/metadata`, `messages/partial`,
`messages/complete`, `updates`, `custom`, `metadata`, `error`. `updates`
and `messages/*` accumulate into message state, then
`convertLangChainMessages` maps LangChain messages to assistant-ui parts.

### Attachments

Files never reach LangGraph. The frontend POSTs to the ingest API on 2030
(`/uploads`, then poll, then `/transcribe`), then inlines the text as an
`[Attached file ...]` marker in the user message. `thread.aui.tsx` hides
that marker from the rendered body while it stays on the wire.

### Tool calls and subagents

Each `message.tool_calls[]` entry becomes one `tool-call` part. Adjacent
calls coalesce into `group-tool` via `groupPartByType`. Tool calls matching
`standalone-tool-call` bypass grouping and render on their own.

The parent agent's only tool is `task`. deepagents collapses subagent
output into a single flat `ToolMessage`, and `streamSubgraphs` is off, so
subagent reasoning and tool calls never reach the UI. The `group-task`
path in `thread.aui.tsx` only activates when `part.messages` is present,
which needs `attachSubagentTranscripts` (not used here).

### Known gaps

- The server always emits `messages/metadata`, which the SDK does not
  treat as known, so each one logs "Unhandled event received".
- `values` is never requested, so the final state reconcile never runs.
- Branching and rewinds run through `getCheckpointId` in `chat-runtime.tsx`,
  which calls `resolveForkCheckpoint` (`lib/langgraph-checkpoints.ts`): it scans
  `threads.getHistory` for the checkpoint whose stored message ids equal the
  truncated sequence, then `onEdit`/`onReload` fork `runs.stream` with
  `checkpoint: { checkpoint_id }`.
- The LangGraph API serves CORS `*` with no auth.

### Frontend

- Build: `npm run build` from `interfaces/frontend` (repo root has no `build` script).
- Lint: `node node_modules\oxlint src` (the `npx` wrapper breaks in PowerShell).
- The LangGraph backend on `127.0.0.1:2024` is user-managed. Do not start or kill it.

##
### Operating procedure
- All code changes must be as minimal as possible to achieve desired outcome
- Any assumptions made when executing tasks must be presented to the user for review before execution
- Do not edit any files that are gitignored without explicit user permission

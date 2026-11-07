# Frontend direction and stack recommendation

Status: reference-interface refresh and audited refinement, 2026-11-07. No recording, ASR, diarization or meeting-participant integration is introduced by this work. See [the UI audit](UI_AUDIT.md) for findings, treatment and verification.

## Interface direction

Use an answer-engine layout: a scrollable response pane above a bottom composer, with sage session navigation and muted teal actions. The composer contains the question field, transcript attachment control, Options, a model selector and Send. It occupies a separate layout row, so it never covers response content. Enter sends a question; Shift+Enter adds a line. Session rows show only title and date.

Responses accumulate above the composer and restore after a reload. Keyword mode shows short exact transcript excerpts; model answers show their first two points with additional material under More detail. Full source text opens in a focus-contained drawer from a passage or citation. Each response retains its own source snapshot, so earlier references still resolve after later questions or a refresh. Supplied timestamps remain distinct from audio playback.

Manrope is self-hosted under `static/fonts/`, with the upstream SIL Open Font License included. Font loading makes no external request. Icons use a small local SVG symbol set; transcript/model output continues to render through DOM text nodes, never trusted HTML. No decorative recordings, fake activity, or unavailable recording controls are shown.

Small screens use an overlay session library and the same bottom composer. Each response names its original session scope. Keyboard focus survives session selection, and dialogs support Escape and focus return. Progress, errors and retry controls appear only when relevant. Search method, context size, notes, import limits and request diagnostics live under Options. Privacy has a separate button in the workspace header, opening a readable panel for local storage, cloud data flow and history controls; it is not part of workspace preferences.

The attachment button uses the existing TXT/SRT/VTT ingestion endpoint and selects the imported session. It is not a general document/image upload or an audio transcription feature. The model menu offers Sources only and the actual configured Gemini identifier; unavailable model access is not represented as connected. Selecting a cloud path exposes its data-flow notice beside Send.

Model setup opens its own focused dialog from the model menu or Options. With no key configured, it shows two steps: add the key to the local environment file and restart the application. With a configured key, it shows the actual model identifier. Check setup refreshes local configuration status through the existing status endpoint; it does not call a model or opt into cloud answers. Semantic-index controls are under Advanced and remain an explicit cloud operation. The panel uses 16px body text, a fixed close header and backdrop dismissal, without mixing in workspace preferences or diagnostics.

Conversation records and source snapshots are saved in browser-local IndexedDB. Draft questions, session scope, search options, model preference and reading position also restore in the same browser profile and origin. Options → Clear conversation removes saved turns, source snapshots and the draft while preserving imported sessions. This is browser-local persistence, with no account synchronization; clearing site data removes it. Credentials are never stored with history.

New responses reveal words progressively after the complete server response has been saved. Refreshing during this reveal restores the full response immediately, with no repeated API call or entrance animation. Reduced-motion preferences bypass the reveal. A request interrupted before completion restores as an interrupted turn with an explicit retry button; failed requests also retain a retry control. Try a sample question submits directly. Questions remain independent API requests: prior UI turns are not sent as model chat context. The reveal is a presentation effect, not provider token streaming.

## Current implementation

The refresh retains Django templates, plain JavaScript and CSS. That is sufficient for this bounded interface and preserves the existing endpoint contracts and launcher. Modern visual design does not require a framework migration. Session filtering is client-side and does not change retrieval scope.

## Recommended direction for the fuller application

| Layer | Recommendation | Rationale and trade-off |
|---|---|---|
| Interactive frontend | React + TypeScript, built with Vite | Reusable components and typed state would help coordinate transcript editing, playback, jobs and eventual live updates. Adds a Node build step and state/data-fetching decisions; migrate when those interactions are implemented |
| Styling | CSS variables and component-scoped styles initially | Preserve deliberate visual tokens without a second styling system. Tailwind is optional, not a prerequisite for a polished UI; avoid adding it alongside a parallel style architecture |
| Application API | Retain Python/Django | Reuse the existing request/security/application boundary. Speech processing stays behind Python adapters and a worker; a visual redesign provides no reason for a backend rewrite |
| Processing | Dedicated background worker within the application codebase | Keep capture/request handling responsive; durable jobs, checkpoints and resource bounds remain required as described in the architecture |
| Storage | SQLite metadata and managed local audio files initially | Fits the single-user baseline. Revisit on measured concurrency, dataset size or shared-deployment requirements |
| Desktop shell | Defer; evaluate a native capture helper or Tauri when Windows capture is proven | A shell can host the web UI, but does not establish microphone/system-audio capabilities, synchronization or Meet access. Rust/sidecar packaging adds work that needs a separate spike |

A React/Vite frontend can build static assets served alongside Django; a second production JavaScript application server is not inherently necessary for this local workspace. Routing and server-rendered features would require additional decisions. Next.js is a candidate if future public pages or server-rendering requirements justify it; those are not current baseline requirements.

React/Vite is the recommended future UI direction, not an accepted migration or an implemented dependency. Keep the source/revision/citation contracts independent of the rendering framework. Do not select versions or claim native capture integration until compatibility is checked in the relevant implementation slice.

## References checked

Official documentation checked 2026-11-07:

- [React: build from scratch](https://react.dev/learn/build-a-react-app-from-scratch) documents Vite with a React/TypeScript template and the routing/rendering trade-offs of a build-tool setup.
- [Django overview](https://docs.djangoproject.com/en/5.2/intro/overview/) describes its application/request/data model.
- [Tauri architecture](https://v2.tauri.app/concept/architecture/) describes its native core and webview architecture; it does not verify this project's capture requirements.
- [Manrope source and license](https://github.com/google/fonts/tree/main/ofl/manrope).

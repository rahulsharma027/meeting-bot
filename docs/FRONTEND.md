# Frontend direction and stack recommendation

Status: reference-interface refresh, 2026-11-07. No recording, ASR, diarization or meeting-participant integration is introduced by this work.

## Interface direction

Use a working research workspace rather than a promotional landing page: persistent dark session navigation, a pale reading canvas, restrained lime accents, and adjacent insight/evidence surfaces. The search composer is the primary action. Session notes remain a separate operation with a visible session prerequisite. Supplied transcript timestamps are explicitly distinguished from audio playback.

Manrope is self-hosted under `static/fonts/`, with the upstream SIL Open Font License included. Font loading makes no external request. Icons use a small local SVG symbol set; transcript/model output continues to render through DOM text nodes, never trusted HTML. No decorative recordings, fake activity, or unavailable recording controls are shown.

Small screens use a collapsible session library and stacked reading surfaces. Inputs, focus rings, reduced-motion behaviour and loading/error states remain part of the interface. Model setup, technical request details and privacy disclosures are available without dominating the search workflow.

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

# Reference workspace UI audit

Date: 2026-11-07. Mode: full. Scope: the session library, search composer, results/evidence, notes controls, disclosures and their responsive/interaction states. Stack: Django templates, plain CSS and JavaScript. No backend/provider migration is part of this audit.

## Baseline evidence

The app-screen inspector measured the existing screen at 1440, 768 and 390 pixels. It reported **3 failures and 3 warnings**: micro-labels, boxed icons, text below 11px, insufficient text contrast, excess empty-panel space and an oversized title. At 1440×900 the result area began at **805px**. Browser interaction checks also confirmed that keyboard session selection moved focus to `BODY`, and changing session scope left old evidence visible with no result-scope label.

| Category | Evidence inspected | Initial result |
|---|---|---|
| Typography | Browser-rendered type sizes, colors, headline and source metadata | Contrast and type-scale fixes needed |
| Surfaces | Composer, split results, empty states, sidebar and focus/hover states | Density, hierarchy and decorative containers needed refinement |
| Animations | CSS transitions, pressed controls and reduced-motion styles | Global press scaling needed to be limited to deliberate actions; slowed-motion verification pending |
| Icons | SVG symbols, repeated header chips, source/citation affordances | Remove boxed decoration; align useful icons consistently |
| Performance | CSS cascade, transitions and existing DOM library rendering | Keep the existing stack; consolidate overrides and preserve focus during rerender |

## Findings and treatment

### Typography and hierarchy

| Severity | Location (baseline) | Before | After (implemented) | Why |
|---|---|---|---|---|
| HIGH | `static/app.css:48`, `:164`, `:221`; `templates/index.html:32`, `:107` | Text as small as 9px; some meaningful captions at 3.2–3.3:1 contrast | Use a small 12/14/16/24px scale, sentence-case labels and text colors meeting 4.5:1 on their actual surfaces | Readable typography and contrast; operational information must not disappear into decoration |
| MEDIUM | `templates/index.html:59`, `:64`, `:93`, `:100`; `static/app.css:98`, `:101`, `:166` | 58px promotional header, anchor links styled as tabs and large illustrated empty states push results below the fold | Compact noun title, honest utility links, short empty-state guidance and earlier results/evidence | App-screen hierarchy; the working content should lead, with no false view-switching affordance |

### Interaction and evidence integrity

| Severity | Location (baseline) | Before | After (implemented) | Why |
|---|---|---|---|---|
| HIGH | `static/app.js:72` | Rebuilding the selected session row discards keyboard focus | Restore keyboard focus to the selected row on desktop and to the question on mobile | Focus continuity; repeated selection must remain usable without restarting navigation |
| MEDIUM | `static/app.js:27`, `:72`, `:153` | The next-search scope changes while earlier results remain unidentified | Persist the result's question/session scope and visibly identify when controls now target another session | Provenance clarity; a previously retrieved answer must not appear to belong to a newly selected session |
| MEDIUM | `static/app.js:27`, `:52`; `templates/index.html:95` | Generic busy state, page-level error and unexplained disabled notes button | Region-specific progress, safe retry, explicit notes prerequisites and preserved last successful results | State clarity; users need to know what is happening and how to recover |

### Surfaces, icons, motion and maintainability

| Severity | Location (baseline) | Before | After (implemented) | Why |
|---|---|---|---|---|
| MEDIUM | `static/app.css:162`, `:176`, `:209`; `templates/index.html:98`; `static/app.js:123` | Repeated tinted icon boxes, large panel void, all passages expanded by default and narrow citation targets | Flat reading surfaces, plain utility icons, a real passage-reference list, first-passage expansion, a bounded desktop evidence reader and 44px citation targets | Surface hierarchy, optical alignment and usable hit areas; long evidence should not leave the answer beside a huge empty column |
| LOW | `static/app.css:27`, `:123`, `:243`, `.answer-toggle` | Global row press scaling; many repeated type overrides; toggle decoration can intercept direct input clicks | Shared spacing/radius/type tokens, action-only press feedback, explicit short transitions, tabular timing/counts and a non-intercepting toggle decoration | Motion restraint, reliable hit areas and a maintainable CSS system; keep the product's evidence distinctive |

## Initial audit direction

The app-screen skill dealt **Achromatic ledger**, seed **77213657**, keeping the existing self-hosted Manrope typeface. No redraw. Use a light open-plane session library, near-black primary action, flat reading surfaces and restrained blue only on source references. The screen's question is: **Which transcript passages support the answer to this question?** Its distinctive element is a source-reference gutter carrying the actual passage number, supplied timestamp and speaker metadata beside readable transcript text.

Data remains the application's real document/retrieval responses. The development corpus has six explicitly synthetic sessions; counts come from those rows, and no audio activity, model success or participant identity is invented.

## Considered but rejected

| Location | Candidate | Rejected because |
|---|---|---|
| Application shell | Rewrite the UI in React during the polish pass | The identified issues can be fixed in the existing stack; a migration would expand scope without resolving them by itself |
| Empty workspace | Automatically show a convincing generated answer or invented waveform | Would misrepresent source/model/audio capabilities; concise guidance is honest and sufficient |
| Results and session rows | Add entrance animations or stronger shadows | These are frequently used reading surfaces; motion and elevation would compete with evidence |

## Verification and verdict

Initial verdict: **Block** because the contrast and keyboard-focus findings were unresolved. Implementation and final verification are recorded below. Live model quality, real audio capture/playback and native-platform integration remain outside this UI audit.

### Final checks

All seven findings above were addressed. Exact checks in the Windows/Chrome development environment:

- `node <design-taste-frontend>/scripts/lint.mjs --app templates/index.html static/app.css static/app.js`: **0 failures, 0 warnings**.
- `node <design-taste-frontend>/scripts/inspect.mjs --app http://127.0.0.1:8013 --out .local/ui-audit/final`: **0 failures, 0 warnings**, at 1440, 768 and 390px. No rule exceptions were allowed. The existing Manrope face was loaded.
- `node --check static/app.js`, `manage.py check`, and `git diff --check`: passed. `python -m unittest discover -v`: **24 tests passed**.
- Focused browser verification at **320, 375, 390, 414, 768, 1024 and 1440px**: no horizontal overflow or mobile header collision; session selection, filtering, keyboard focus and mobile return-to-question behaviour passed.
- Actual offline keyword search, zero-result search, passage-reference navigation and original question/scope labels passed. Changing scope retains and identifies prior results. A failed request retried after a scope change sent the exact original payload.
- Synthetic provider-shaped responses verified cited-answer/notes rendering, HTML-like text rendered literally, 44×44px citation targets, operation progress, model prerequisites and error/retry recovery. These were UI fixtures, not live model calls.
- Chrome Animation playback set to **10%**: the toggle progressed through an intermediate position to its 14px endpoint; frames were visually inspected. Hover and focus states were inspected, primary press settled at `scale(.96)`, and reduced motion removed transition duration. No entrance or repeated row animations were added.

| Category | Final evidence | Result |
|---|---|---|
| Typography | Inspector measurements and desktop/tablet/phone renders | 24px title; five sizes in use (12/14/16/17/24px); no contrast or micro-label findings |
| Surfaces | Empty, zero-result and populated screenshots; reader dimensions | Results begin at **520px**, versus 805px before, at 1440×900; the desktop evidence body is bounded to 544px and scrolls its real content |
| Animations | Slowed toggle frames, hover/pressed sampling and reduced-motion checks | Short reversible feedback; action press at .96; reduced-motion transition duration 0s |
| Icons | Actual SVGs and citation/source controls at rendered sizes | Plain current-color icons, no tinted chips; decorative toggle track cannot intercept the input |
| Performance | Source lint, CSS review and console checks | No transition-all, speculative will-change, new runtime dependencies or JavaScript page errors |

### Screenshot critique of the initial audited pass

The result and its evidence now share the first desktop screen rather than following a promotional header. Composer, reading surface and disclosures share their canvas edges. Source counts and reference rows come from the same retrieval response; timestamps retain their supplied precision, and zeros remain explicit. Blue is limited to evidence references and focus, with a near-black primary action. No chart, legend, invented activity or numerical growth claim is present. The phone folds the library, preserves the title and question, and stacks the reading surfaces without horizontal scrolling.

[Desktop](screenshots/desktop.jpg) and [mobile](screenshots/mobile.jpg) documentation screenshots contain only the synthetic development corpus. Intermediate reports, fixtures and motion frames remain ignored local artifacts.

Final verdict: **Approve for the audited reference-interface scope**. No actionable findings remain in the verified scope. **Not verified:** physical touch devices, Safari/Firefox, macOS font rendering, assistive-technology sessions, live model quality or native audio/platform integrations. This UI audit is not a full WCAG conformance certification.

## Teal palette refinement

The current visual direction supersedes the initial achromatic palette with muted teal actions and source references, sage navigation, a pale mint evidence surface and clearly tinted selected sessions. Layout, typography, focus handling, result provenance and retry behaviour remain as audited. Status errors retain their distinct red treatment.

The palette uses shared CSS tokens. Measured text contrast: white on the primary teal **6.38:1**, primary hover **8.82:1**, selected-session text **6.95:1**, evidence metadata **5.38:1**, source references **5.30:1**, and sidebar metadata **5.04:1**. The design inspector at 1440, 768 and 390px and source lint both report **0 failures and 0 warnings**. Empty/zero-result and actual keyword-result checks passed with no JavaScript page errors; the result area remains at 520px and the evidence reader at its 544px bound. Desktop and mobile screenshots were refreshed from the synthetic corpus and visually inspected.

## Answer-engine layout and progressive disclosure

This is the current interface, superseding the initial split reading surface described above. The main workspace uses a response pane and a bottom composer containing the question, attachments, Options, Models and Send. Session navigation shows title/date only. Advanced configuration, model setup, privacy, notes and diagnostics are inside Options; full passages are inside a source drawer. Response bodies keep short excerpts or the first two generated points, with further generated detail expandable.

Browser checks verified a pinned composer at 320, 375, 390, 414, 768, 1024 and 1440px, plus a 390×500 viewport. Response content scrolls independently (631px visible area over 1,581px of test content), with no horizontal overflow. Enter/Shift+Enter, overlay session selection, native dialog focus/Escape, actual keyword retrieval, duplicate transcript attachment, configured-model fixtures and earlier-turn source references passed. There were no JavaScript page errors. Source lint, JavaScript syntax and the Django system check passed. The existing 24-test suite passed during this simplification work.

The quiet initial response area is intentional; it reserves space for requested answers rather than adding explanatory cards. It is acceptable for an empty answer workspace to contain open space. Screenshots use only the synthetic development corpus. Model tests use route fixtures; no live compatibility, generation quality, audio processing or token streaming is established. Prior turns are not model conversation context.

## Response reveal and continuity

The latest refinement adds a short word-by-word reveal for new responses, with source references appearing when their associated text finishes. Reduced motion and background tabs bypass the effect. Completed history restores without animation. The complete answer and its source snapshot are written to browser-local IndexedDB before presentation begins, so a refresh during reveal retains the whole answer. Interrupted requests restore with an explicit retry rather than issuing another model call automatically. Options includes Clear conversation; imported sessions stay available.

The focused Chrome regression passed reveal/refresh, source integrity, draft/preferences, interrupted/failed retry, safe text rendering and history clearing, plus responsive composer checks at 320, 390, 768 and 1440px. No runtime dependency, icon system or styling system was introduced. See [verification](VERIFICATION.md) for the reproducible test and browser-local persistence limits.

## Model setup clarity

The model-menu setup action previously opened the full settings dialog at a lower accordion, mixing connection instructions with unrelated preferences. It now opens a focused model dialog with 16px body text, a clear configuration status and two setup steps. Configured models show their actual identifier; semantic indexing stays under Advanced. The fixed header and outside-click dismissal apply to both settings and model dialogs. A configuration check refreshes local status without enabling cloud answers or calling a provider. Focused desktop/mobile fixture checks and the existing history regression passed; see [verification](VERIFICATION.md).

## Privacy placement

Privacy information now has its own header control and dialog rather than occupying workspace preferences. The separate panel uses 16px text and three sections for local storage, cloud processing and user controls. The source-only/cloud distinction remains visible beside the relevant actions. The fixed close header, outside-click dismissal and focus return follow the existing dialog behavior. Desktop/mobile checks at 320, 390, 768 and 1440px passed without header overlap or horizontal overflow.

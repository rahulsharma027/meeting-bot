# Verification record

Baseline executed: 2026-11-04. Environment: Windows, Python 3.15.1, Django 5.2.18. Python 3.15 is experimental for this pinned Django release; the documented Python 3.12–3.14 environment has not yet received complete project-specific verification.

## Recorded checks

| Check | Result |
|---|---|
| `python run.py --setup-only` | Installed pinned dependencies, initialized SQLite, and loaded six synthetic sessions |
| Repeated setup | Reused the environment and preserved existing source data |
| `manage.py check` | No issues reported |
| `python -m unittest discover -v` | 24 tests passed |
| `python evaluate.py` | Offline application BM25 evaluation completed |
| Responsive layout | No horizontal overflow observed at 320, 375, 768, 1024, and 1440 pixels |
| Browser source search | Returned dated passages containing original and revised task commitments |

Tests cover TXT/SRT/VTT parsing, source timestamps, duplicate ingestion, versioned chunk regeneration, retrieval-mode separation, rank fusion, invalid vectors, incompatible indexes, forged citations/quotes, missing credentials, CSRF, and upload validation.

## Retrieval baseline

The application evaluation uses 12 synthetic development questions, document-level relevance labels, and a budget of four retrieved chunks.

| Metric | Recorded value |
|---|---|
| Document recall | 0.9306 |
| Document precision | 0.4306 |
| Mean reciprocal rank | 0.9583 |
| Hit rate | 1.0000 |

Documents are deduplicated after chunk retrieval. Precision uses the number of returned distinct documents rather than a fixed document k. These results are not held-out benchmark results or generated-answer accuracy. See `evaluation/application-baseline.json`.

The exploratory TF-IDF results in `evaluation/tfidf-baseline.json` use a different document-level retriever and retrieval budget. They do not measure the application BM25 or embedding implementation and should not be directly compared as identical experiments.

## Verification limits

- Live provider compatibility, real document/query embeddings, semantic/hybrid measurements, generated answers, and generated notes remain unverified.
- Source support, useful abstention, prompt-injection behaviour, action ownership, and date interpretation need live evaluation against `evaluation/answer_checks.json` and additional held-out examples.
- Browser file-picker automation did not complete; upload endpoints and duplicate handling passed HTTP-level tests.
- Model-backed latency percentiles, memory requirements, cost, and production throughput have not been measured.
- Audio capture, ASR, diarization, shared-user authorization, and Google Meet bot joining are planned capabilities, not verified features.

Mocked responses test provider contracts and orchestration only. `evaluate.py --live` performs actual embedding calls for retrieval evaluation; generated-answer quality requires a separate source-support review.

## Architecture-review rerun: 2026-11-05

- Existing environment: Python 3.15.1 / Django 5.2.18 (the same experimental Python compatibility caveat applies).
- `manage.py check`: no issues.
- `python -m unittest discover -v`: all 24 existing tests passed.
- `python evaluate.py --output .local/architecture-review-bm25.json`: reproduced recall 0.9306, precision 0.4306, MRR 0.9583 and hit rate 1.0000. The rerun report is an ignored local artifact; the tracked baseline is unchanged.
- No live provider calls, model downloads, audio processing, UI layout checks or Google Meet integration were run in this review. Proposed architecture/contracts/ADR/roadmap describe future acceptance gates, not new verified features.

## Reference-interface refresh: 2026-11-07

- `manage.py check`, JavaScript syntax checking, and all 24 existing tests passed.
- Headless Chrome checks at 320, 375, 414, 768, 1024 and 1440 pixels found no horizontal page overflow; the primary search target remained 46 pixels tall. Desktop/mobile screenshots were visually inspected.
- Browser checks exercised session filtering/selection, mobile library expansion/collapse, sample questions, actual offline keyword retrieval, model-setup disclosure, and disabled AI controls without a key. No JavaScript page errors were observed.
- Synthetic route fixtures exercised generation/notes/action rendering, citation navigation, loading/error recovery and literal rendering of HTML-like text. These checks did not call or validate a live model.
- Preview data came from a separate synthetic-only database. Public screenshots contain synthetic corpus data only. Browser tools, preview databases and intermediate screenshots remain in ignored local storage.
- Live model quality, native audio capture/playback, ASR/diarization and meeting participation remain outside this interface verification.

## UI audit and refinement: 2026-11-07

The [full UI audit](UI_AUDIT.md) records the initial failures, seven findings, implemented treatments and remaining verification boundaries. Design-skill source lint and browser inspection finished with **0 failures and 0 warnings**. At 1440×900, the result area moved from 805px to 520px from the page top.

Focused Chrome checks passed at 320, 375, 390, 414, 768, 1024 and 1440px, including keyboard focus after selection, citation navigation, result-scope preservation, retrying the captured original request, zero results and a bounded evidence reader. Toggle/pressed states were inspected at 10% animation playback and with reduced motion. No JavaScript page errors were observed. All 24 existing tests, the Django system check and JavaScript syntax check passed.

Actual retrieval checks used the isolated synthetic corpus; model-backed UI states used synthetic route fixtures. No live provider or new audio functionality was verified. Refreshed public screenshots use synthetic corpus data only.

The subsequent teal palette refinement passed source lint and desktop/tablet/mobile design inspection with zero failures or warnings. Selected-session, primary-action, evidence and reference text color pairs measured 5.04:1–8.82:1 contrast. The targeted empty/zero-result, actual keyword retrieval, hover/pressed and bounded-reader checks passed with no JavaScript page errors. This theme-only pass did not change application logic; the prior 24-test result remains the recorded code baseline.

## Answer-engine layout: 2026-11-07

Browser checks passed for the bottom composer and independently scrolling response history at seven widths from 320 to 1440px, plus a short 390×500 viewport. Checks covered Enter to send, Shift+Enter for a newline, original-source resolution from earlier responses, model selection/cloud disclosure, session navigation, Options/source dialogs and duplicate TXT transcript attachment through the actual upload endpoint. No JavaScript page errors or horizontal overflow were observed. JavaScript syntax, source lint, the Django system check and diff whitespace checks passed; all 24 existing tests passed during the preceding simplification pass.

Public screenshots were refreshed from the isolated synthetic corpus. Generation/model menu tests used synthetic route fixtures. This pass used browser-page memory; persistent history and response reveal are covered below. Each API question remains independent, and no token streaming, model availability or live answer-quality claim is established by these UI checks.

## Persistent conversation and response reveal: 2026-11-07

`tests/browser_history.cjs` passed in headless Chrome against the isolated preview, using synthetic status/answer fixtures and real browser IndexedDB. It verified direct sample submission, partially revealed answer text, complete persistence before reveal, refresh during reveal without another API call, restored source snapshots and safe literal source text, saved drafts/scope/options/model preference/reading position, interrupted requests with explicit retry, failed-request recovery, storage-unavailable fallback, and clearing history while retaining sessions. Response history and a pinned composer remained intact at 320, 390, 768 and 1440px without horizontal overflow. No JavaScript page errors were observed.

Run with Playwright installed and Chrome available: `node tests/browser_history.cjs`. `TL_UI_URL` sets the isolated preview origin (default `http://127.0.0.1:8013`); `PLAYWRIGHT_MODULE` optionally points to an existing Playwright installation. No browser dependency or local fixture database is committed. Model responses in this test do not establish live provider behavior.

Both application scripts and the browser regression passed JavaScript syntax checks. Source lint reported zero failures/warnings; the Django system check and all 24 existing Python tests passed using the project virtual environment. Persistence is per browser profile/origin and is not synchronized to other devices. The progressive reveal uses the completed JSON response; it does not introduce server token streaming.

Actual offline sample search returned four passages, all restored after reload with the original full source text. Updated desktop/mobile screenshots were visually inspected. The rendered design inspector reported zero failures/warnings at 1440, 768 and 390px.

## Settings dialog scrolling: 2026-11-07

The settings dialog now keeps its header outside the scrolling content region. Focused Chrome checks at 320×500, 390×844, 768×900, 1024×900 and 1440×900 verified that expanding every settings section and scrolling to the bottom leaves the 44px close button stationary, unobstructed and clickable. Click/Escape closing, focus return, model-setup navigation and absence of horizontal overflow passed, with no JavaScript page errors. Desktop/mobile scrolled states were visually inspected. This layout-only change adds no API behavior or runtime dependency.

Workspace settings also dismisses on a backdrop click/tap. Focused Chrome checks at 1440×900 and touch-enabled 390×844 verified outside dismissal before/after scrolling, preserved preferences, focus return, Escape and the close icon. Inside clicks and drags starting inside the card do not dismiss it. No JavaScript page errors were observed; JavaScript syntax and diff whitespace checks passed.

## Focused model setup: 2026-11-07

Model setup now opens a separate dialog rather than scrolling the workspace options to an accordion. Chrome checks at 320×500, 390×844, 768×900 and 1440×900 verified the two-step/no-key state, configured model display, 16px body text, fixed close header, backdrop dismissal, Escape, focus return and no content overflow. Status refresh and explicit index creation used synthetic endpoint fixtures; checking status issued no question/index request and kept Sources only selected. The configured panel keeps indexing under a closed Advanced disclosure. Desktop/mobile captures were visually inspected, and no JavaScript page errors were observed.

The existing conversation-history browser regression passed after this change, including drafts/preferences/citations, interrupted/failed retry and responsive history. JavaScript syntax, source lint (zero failures/warnings) and diff whitespace checks passed. No provider compatibility or live model quality was verified by these UI fixtures.

## Privacy navigation and transcript preparation: 2026-11-07

Data & privacy moved from Options to a separate Privacy control in the workspace header. Focused Chrome checks at 320×500, 390×844, 768×900 and 1440×900 verified its removal from Options, non-overlapping header controls, readable dedicated content, stationary close button while scrolling, click/Escape/backdrop dismissal, focus return and absence of horizontal overflow. Desktop/mobile captures were visually inspected; no JavaScript page errors were observed. JavaScript syntax, source lint and diff whitespace checks passed.

The [transcript preparation guide](TRANSCRIPT_WORKFLOW.md) documents the current text-import workflow and candidate local speech tools, based on upstream documentation checked on this date. The synthetic TXT template was parsed with the actual importer and retained both speaker labels and timestamps. No speech runtime was installed, no private recording was processed, and no transcription-quality or hardware-performance claim was validated in this UI/documentation change.

## Self-hosted meeting-bot assessment: 2026-11-07

The product requirements specify local/self-hosted capture for a joining Google Meet bot, with stable anonymous speaker labels and recordings/transcripts/questions in one portal. Requirements and the roadmap now link to the [meeting-bot flow and pilot gate](MEETING_BOT.md). Current primary sources were checked for Google's announced Meet Media API shutdown and Vexa's self-hosting, capture-only and custom speech interfaces. These are upstream claims and an integration proposal, not verified TranscriptLens capabilities.

A working Linux container engine remains a deployment prerequisite. No services, images, speech models or bot dependencies were installed, no real meeting was joined, and no recording was made. This documentation-only assessment passed diff whitespace checking; application tests were not rerun for it.

## Release verification: 2026-11-07

Before committing the combined interface/documentation update, the Django system check and all 24 existing tests passed in the project virtual environment. JavaScript syntax checks and the conversation-history Chrome regression passed. Focused model-setup/privacy checks and actual offline sample retrieval also passed; public screenshots were refreshed from the isolated synthetic corpus. No live cloud model or meeting-bot capability was verified by these checks.

## Capture-only pilot kit: 2026-11-07

The standalone helper and Compose deployment are described in [the capture pilot guide](CAPTURE_PILOT.md). Upstream source/API inspection used Vexa commit `6b26f7b921756d6db128d42cd70b4b7046381407`; container manifests and the browser sandbox profile are pinned. The actual profile was fetched and its canonical-file checksum verified. `docker compose config --quiet` accepted the generated local configuration without starting containers.

Nine synthetic local-HTTP/unit tests cover explicit recording approval, Meet URL validation, capture-only request fields, retained receipts after an ambiguous join, stop/export contracts, recording ownership, blocked redirects/off-origin media, partial export preservation, credential-safe output, idempotent preparation, atomic receipt replacement and refusal of remote Docker endpoints. These tests do not prove upstream container compatibility or actual capture. The Django system check and Python regression suite passed before packaging; no live meeting, recording, GPU inference or portal integration was exercised.

The portable ZIP contains only the helper, Compose file and guide. Generated credentials, downloaded source/profile files, local session receipts and recordings are excluded. No image was pulled or service started during validation on the development machine. The next dependency is running the kit on the intended capture PC and observing a real admitted bot and usable audio.

## Capture-host deployment and guest-join attempt: 2026-11-07

The kit was transferred over a host-key-verified SSH connection and its archive checksum matched. On the Windows/WSL2 capture host, Docker Engine 29.9.2, Compose 5.6.1 and Python 3.12.3 were observed. The app, database and storage became healthy; storage initialization and scoped API-key provisioning succeeded. Authenticated bot/recording API reads succeeded. Runtime configuration confirmed recording enabled, transcription disabled, no speech endpoint and the LLM kill switch enabled. Published image digests were independently verified against registry manifest bytes; no digest verification was disabled.

With call-specific recording approval, one guest bot was requested. Its stored meeting URL matched the request and its API state reached `awaiting_admission`, but the host saw no admission request. The isolated bot display showed the Google Meet product landing page. The attempt was stopped and verified `failed`, with zero recording records. No successful admission, recording, audio quality, speaker attribution or transcript processing was established. The screenshot and call-specific state remain ignored private diagnostics, not public fixtures.

Google's guest-join documentation and Vexa's authenticated-bot guide were checked. An account-related restriction is a possible cause, not a proven diagnosis of the redirect. The next route uses a dedicated Google account with the supported Compose provisioning/authentication flow; upstream Lite does not support that flow. Account sign-in and any verification remain human actions. No account password, verification code or browser session was collected during this attempt.

## Dedicated-account setup: 2026-11-07

The dedicated Google account's human sign-in completed; the isolated provisioning container exited zero and its success receipt was checked without inspecting cookie values or account credentials. Its temporary SSH tunnel was closed. The separate [authenticated capture deployment](AUTHENTICATED_CAPTURE.md) passed Compose validation, reached healthy state for all seven long-running services, and passed upstream's real userdata-prefix permission checks. Thirteen auth-essential items were exported only to local storage, with nonempty mandatory-object checks. Private scoped gateway API access succeeded. The idle Lite services were stopped and their data volumes retained. No agent/model services were started and transcription remained disabled.

The private Docker control network initially prevented loopback port publication; adding a separate edge network to gateway resolved it. Runtime, database and admin-api still have no published ports, and spawned bots use a separate network. This is a setup result, not proof of authenticated Meet admission or usable recording. The call-specific retry remains a separate live test.

The first authenticated retry exposed an upstream session-continuity bug: the browser launch merges the guest `--incognito` flag into authenticated mode. The isolated bot display again showed Google's public Meet product page. The bot's `needs_help` event was rejected as an illegal lifecycle transition, leaving misleading `joining` state. The attempt was stopped and verified `failed`. A guarded derived image now removes incognito only for authenticated invocations, preserving anonymous-mode behavior. The image build verified the original compiled-file hash, both launch modes and JavaScript syntax. The 33-test prototype/capture-client regression suite also passed with synthetic loopback HTTP enabled. The corrected image then restored the session through the actual bot launch path and passed upstream's real Google logged-in validation without joining a meeting. Corrected Meet admission and recording still require the live test.

## Corrected authenticated recording test: 2026-11-07

The approved retry using the corrected browser reached `active`; the host explicitly confirmed the bot in the participant list. The test was stopped and both meeting and recording finalized as `completed`. Export checked meeting ownership and a same-origin media path, retained the original WebM, and wrote a byte/hash receipt. The 1,483,612-byte file matched its SHA-256 after encrypted transfer to the laptop. An isolated local Chrome context, with all network requests blocked, decoded 120.18 seconds of stereo audio at 48 kHz. RMS was approximately 0.0502; 85 of 241 half-second windows exceeded an RMS threshold of 0.004. These are decode/non-silence measurements, not speech accuracy, audible-quality or clipping judgments.

The operator reported only one speaker. No ASR, diarization or cloud processing was performed. The source audio, hashes, call receipts, account material and private diagnostics remain ignored/private. A real two-speaker attribution test, listening review, full-service restart/recovery, speech worker and portal integration remain outstanding. This result verifies a bounded capture path, not the complete meeting-assistant acceptance gate.

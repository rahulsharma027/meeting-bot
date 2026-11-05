# Component roadmap

Development begins with architecture and contracts, followed by one independently verifiable component at a time. The existing text-transcript prototype remains a reference implementation during this process.

| Stage | Component or deliverable | Verification gate |
|---|---|---|
| 1 | Architecture, requirements, and component contracts | Review boundaries, data flow, open decisions, and acceptance criteria before implementation |
| 2 | Session/source storage and normalized segment contracts | Preserve originals, stable IDs, timestamps, revisions, and idempotent writes |
| 3 | Recorded-file ASR adapter | Process representative authorized recordings; measure text accuracy, timing, runtime, and memory |
| 4 | Speaker diarization and alignment | Verify speaker consistency, overlap, uncertainty, corrections, and source playback locations |
| 5 | Finalized transcript indexing | Verify chunk provenance, embedding compatibility, cache invalidation, and scoped retrieval |
| 6 | Notes and cited Q&A | Evaluate source support, missing information, explicit action ownership, and revised commitments |
| 7 | Live Windows capture | Validate synchronization, partial/final revisions, queue lag, pause/stop, and recovery |
| 8 | Google Meet participant adapter | Verify admission, visible recording, media delivery, end-of-session finalization, and integration errors |
| 9 | End-to-end validation | Reproducible setup, representative evaluation, performance measurements, and documented limitations |

## Working method

For each stage, define its inputs and outputs, resolve its immediate dependencies, implement one complete path, and record real verification results. Avoid broad feature expansion or optimization without a measured need. Test doubles verify contracts; actual runtime/integration checks establish compatibility and quality.

## Current checkpoint

- Proposed architecture and requirements are documented.
- A text-transcript reference prototype and synthetic development corpus are present.
- Twenty-four reference-prototype tests and an offline keyword evaluation have passed.
- Real embeddings/generation, audio processing, speaker tracking, live capture, and meeting participation require separate verification or implementation.

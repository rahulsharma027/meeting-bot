# Requirements and scope

## Product objective

Provide a local-first workspace for lecture and meeting recordings, speaker-attributed transcripts, reviewable notes, and questions answered with source evidence.

## Core capabilities

| Capability | Required behaviour |
|---|---|
| Session management | Keep title, kind, date, processing state, and source references for each session |
| Recording | Preserve original authorized audio with visible recording state and stop/pause controls |
| Transcription | Convert audio to timestamped text; distinguish provisional and finalized segments |
| Speaker attribution | Associate speech with consistent speaker IDs; support correction and explicit naming |
| Provenance | Connect transcript passages and generated claims to their source and audio location |
| Notes | Summarize lecture concepts, meeting decisions, and explicitly assigned action items |
| Retrieval | Find relevant passages within one session or across selected sessions |
| Q&A | Generate evidence-based answers and handle insufficient information explicitly |
| Persistence | Preserve recordings and finalized transcripts through processing failures |
| Evaluation | Assess ASR, speaker attribution, retrieval, and generation independently |

## Platform direction

Windows is the initial local recording target. Google Meet is the first intended meeting platform. Local capture and a visible participant bot are separate capture adapters; the bot integration is a later milestone.

## Initial constraints

- Component-level development follows the architecture review.
- Existing text-transcript code is a reference implementation, not a completed meeting bot.
- Use synthetic or authorized test material.
- No shared-user or public deployment is part of the initial local architecture.
- Speech runtime, hardware requirements, diarization model, and bot integration remain subject to evaluation.

## Confirmed processing policy

Architecture review, 2026-11-05: local-by-default ASR and diarization, with explicit cloud opt-in, are confirmed. The proposed architecture extends the same default and opt-in boundary to embeddings, notes and Q&A. Opt-in identifies provider, operation, sources and transmitted data. Recording approval and cloud approval are separate. The prototype's optional cloud adapter does not establish this complete policy boundary; a configured key alone must not authorize future background transfers.

The immediate use case includes technical meetings and conversations. Lecture support remains a product objective. Languages, typical duration, speaker count and Windows hardware have not been established; do not infer a language or promise real-time/local-model performance from this use case.

## Reliability and evidence requirements

- Preserve accepted original recording bytes independently of decoding/transcription success; retain recoverable partial capture with an explicit completeness status.
- Use a consistent audio timeline with source/media mappings, pause/loss gaps and declared timestamp precision.
- Keep capture, source availability, job progress and derived-artifact state independent. Finalized transcript text is not a claim of human verification.
- Publish transcript corrections as immutable revisions with actor/reason and split/merge provenance; stale affected indexes/results without changing historical citations.
- Accept duplicate events/retries idempotently. Fence cancelled/obsolete attempts and use bounded queues, retry counts and resource limits.
- Preserve uncertain/overlapping speakers. Diarization labels are not real names; missing owners, dates and commitments must not be invented.
- Require explicit session scope for retrieval and claim-level evidence for generated content. Source-existence checks do not establish semantic support.
- Keep original audio, private text/results, secrets, downloads and caches out of Git. Define backup, explicit deletion and eventual retention alongside persistence.
- Keep recording state, approval basis, pause/stop and local/cloud data flow visible. Transcripts and model outputs cannot authorize external actions.

## Decisions still needed

| Decision | Default for architecture review | Needed before |
|---|---|---|
| Languages, code-switching, audio conditions and technical vocabulary | Unknown; build a small authorized representative sample set | ASR/model evaluation |
| Windows CPU/RAM/GPU and representative duration/concurrency | No hardware/performance promise; one active capture provisionally | Runtime selection and resource limits |
| Quality targets and live latency | Measure offline first; no numerical quality claim yet | Declaring an adapter acceptable |
| Retention and backups | No automatic source expiry; explicit deletion; stopped-app backup initially | Private-data pilot |
| Mixed audio versus separate microphone/meeting tracks | Preserve available tracks; do not promise platform identity | Windows capture |
| Speaker names and cross-session identity | Anonymous session IDs plus explicit correction; no cross-session voice matching | Speaker-attribution UI |
| Google Meet route and account access | Deferred; no assumed desktop API or platform capability | Meet adapter design |

Speech local/cloud policy is resolved; the matching text-processing policy is proposed. Local speech runtimes and a local generation option remain unselected and unverified. A deployment that cannot run a chosen local stage must report that limit, rather than silently send data to cloud.

## Future extensions

Calendar-triggered attendance, email delivery, external task creation, voice responses, and multiple meeting platforms are outside the initial scope. They require separate requirements and authorization boundaries.

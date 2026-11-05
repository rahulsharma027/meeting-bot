# Component roadmap and acceptance gates

Architecture first. The items below are proposed implementation work after review, not completed capabilities. The text prototype remains a reference; no product features are added during this phase. See [architecture review](ARCHITECTURE_REVIEW.md), [architecture](ARCHITECTURE.md), and [contracts](CONTRACTS.md).

## Ordered implementation

| Order | Bounded component and dependency | Acceptance / evaluation gate |
|---|---|---|
| 1 | Review architecture, state model, contracts and ADRs | Agree on local/cloud policy, durability, correction/citation semantics and first slice. Document unresolved workload/quality questions without blocking independent storage design |
| 2 | Session/source storage, minimal durable jobs and normalized revision fixture | Exact original hash/bytes survive reopen and failed downstream work; duplicate/conflicting requests behave correctly; fault-injected file/DB boundaries reconcile; stale leases/cancellation cannot publish; explicit deletion and backup/restore verified |
| 3 | Decode and playback source resolver | Preserve originals; supported formats/size/duration limits documented; decode/resampling maps correct for known markers; interval/gap/untimed playback works; unknown IDs/path escapes denied; no ASR required |
| 4 | Recorded-file ASR adapter | Current official runtime/model/license compatibility recorded. Representative authorized technical audio covers declared language, jargon, silence/noise and long input. Measure WER/CER as appropriate, technical-term errors, segment timing error, real-time factor, peak RAM/VRAM, failures/cancellation. Choose numerical release targets after baseline and before accepting the adapter |
| 5 | Diarization and alignment | Label speaker turns/overlap in representative samples; report DER/JER with collar/overlap policy, speaker-confusion and timing distributions. Test unknown speakers, overlapping speech, run-label remapping, correction/split/merge history and degraded ASR-only output. Never infer participant names |
| 6 | Final transcript persistence/correction UI and revision-aware indexes | Publication/correction races, immutable citations, currentness notices and draft exclusion verified. Chunk spans round-trip exactly. Scope tests isolate selected sessions. Incompatible models/task/dimensions rejected; unchanged embedding inputs reused; index publication atomic; keyword works without models |
| 7 | Notes and cited Q&A | Verify any chosen local or opt-in cloud adapter on actual calls. Held-out passage relevance and question sets cover unanswerable questions, conflicting/revised commitments, prompt injection, owners/dates and technical terms. Report claim support/citation coverage, unsupported-claim rate, action precision/recall and abstention precision/recall; source existence alone is insufficient. Oversized notes disclose/reject incomplete coverage |
| 8 | Windows capture and live transcript drafts | Verify actual target machine's microphone/meeting tracks. Measure durable-write exposure, gaps, drift and inference lag over representative duration. Test pause/resume/stop, device loss, disk full, overload and crash recovery; bounded memory and visible interruption required. Prove capture remains independent of stalled ASR/generation |
| 9 | Visible Google Meet adapter | First verify current official integration/access route and licensing/terms; choose build/buy route in ADR. Demonstrate admission/denial, visible recording/approval, media/timeline delivery, reconnect/disconnect, stop and finalization. Participant metadata is not assumed reliable identity. No claim of bot support until real authorized flow passes |
| 10 | End-to-end pilot and packaging | Reproducible setup; exact runtime/model hashes and attribution; local/cloud consent enforcement; private-data exclusion; recovery/deletion/restore; desktop/mobile status/playback; measured performance and documented limits |

## Evaluation discipline

Correctness invariants (source-byte preservation, scope isolation, revision integrity and bounded resource behaviour) are hard gates. Empirical targets require a declared workload and hardware. Do not invent WER, speaker accuracy, throughput or latency guarantees before representative measurements. Use authorized samples of actual technical conversation and separate held-out material; report sample duration, languages, speaker counts, devices/noise and label conventions. Hand-review evidence support separately from retrieval relevance. Record uncertainty and failure cases, not only averages.

Freeze initial numerical quality/runtime targets after the baseline and before model/adapter acceptance. Until targets and workload are decided, an experiment is a measured candidate, not a production-ready stage. Do not upgrade the 12 synthetic development queries to a benchmark or interpret document-level metrics as passage/answer correctness.

Before recommending a particular runtime/model/platform API, consult current official documentation and record date, version/artifact identity, supported formats/hardware, license/attribution, access restrictions and relevant data/pricing terms. A fake adapter tests contracts only. Reuse compatible loaded models/cached embeddings; optimize only measured bottlenecks.

## First component recommendation

Implement **recorded-source acceptance and recovery** after architecture review: create one session, accept one small synthetic recording into immutable managed storage, record its byte hash/manifest, enqueue a minimal inspection job, and retrieve its source status after restart. This establishes the boundary every speech/capture adapter needs without choosing a model.

Keep the slice small: one declared fixture format, session/source records, a staged-file commit/reconciliation path, minimal job lease/checkpoint semantics, and one normalized transcript-revision fixture to prove future source mapping. A test worker can deliberately fail inspection; it must not claim ASR or diarization. No new live recorder, meeting bot, vector backend or generation workflow belongs in this slice.

Acceptance scenarios:

1. Import/reopen and compare source hash/bytes; repeat request and get the same source/job; reject reuse of the key with changed bytes. Same bytes attached to another session keep distinct provenance.
2. Inject failure before/after file rename and DB commit; restart/reconcile without orphaning or silently deleting accepted original bytes. Unsupported/failed inspection retains the original and a safe error.
3. Cancel/fail/retry the inspection job, expire a lease and inject a stale result; source remains available and only the valid attempt publishes.
4. Resolve the synthetic segment's declared media interval without inventing word times; untimed text reports no playback mapping. Demonstrate expected-revision conflict with the fixture, without building the correction editor.
5. Explicit deletion prevents late work/references from restoring content. Stop app/worker, back up source+DB+manifest, restore into a fresh data directory and verify references/hashes.

Record what passed, actual environment and limits before starting the decoder/ASR slice. Storage limits, recovery policy and data location become concrete implementation choices here; model choice and live-capture sizing can remain open.

## Current checkpoint

On 2026-11-05 the existing system check, 24 prototype tests and offline BM25 evaluation were rerun successfully. These cover the reference text path and mocked provider contracts. Live embeddings/generation, speech, speaker tracking, audio playback/capture and Meet participation remain unverified or unimplemented. See [VERIFICATION.md](VERIFICATION.md).

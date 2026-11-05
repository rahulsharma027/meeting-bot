# Component data and lifecycle contracts

Status: proposed, 2026-11-05. These are logical records, not implemented schemas or HTTP endpoints. Implement only the subset needed for the next bounded component. [ARCHITECTURE.md](ARCHITECTURE.md) owns boundaries; this document defines publication and provenance invariants.

## Shared conventions

- IDs are opaque application-generated values. A digest identifies bytes, not a person, session or approval.
- Offsets are integer microseconds; intervals are half-open `[start_us, end_us)`. Capture mappings include sample counters/rates. UTC wall-clock times are separate. Missing times are null, never default zero.
- Events/results record schema version, producer and effective configuration. Engine confidence includes its definition; unknown confidence is null.
- Commands carry an operation/session-scoped request key. Same key/payload returns the prior result; changed payload is a conflict. Optimistic updates require an expected revision.
- References use internal asset IDs, not client-controlled paths. Validate finite limits on bytes, times, event sizes and results at boundaries.

## Core entities

| Entity | Minimum proposed fields | Invariants |
|---|---|---|
| Session | ID, title/kind, optional UTC start/timezone, lifecycle, authorization reference, policy version | Unknown dates stay unknown; several sources/capture attempts may belong to one session |
| AuthorizationRecord | Session, approval basis/reference, actor, timestamp, purpose | Documents basis; does not infer universal participant consent |
| ProcessingPolicy | Version, stage, local/cloud mode, provider, allowed sources, opt-in/revocation times | Local default; capture approval is not cloud approval |
| SourceAsset | ID/session, kind, original filename, internal object reference, SHA-256, bytes, media metadata, state, import/capture request | Exact imported originals; duplicate bytes may share storage but retain distinct session/provenance links |
| CaptureAttempt / AudioBlock | Attempt/track/sequence, asset/range, sample format/count/rate, session interval, clock-map version, durable checkpoint | Unique `(attempt, track, sequence)`; samples and declared gaps reconcile |
| TimelineMap / Gap | Track/source, session interval, media/sample interval or gap, transform/version, reason/precision | No media is invented for pause/loss; mappings compose through decoding/resampling |
| ProcessingRun | Stage, adapter/runtime/model IDs and artifact hashes, config hash, sources, policy snapshot, start/end/usage | Distinct reruns; effective configuration excludes secrets |
| Job | ID/type/input/dedupe key, state, attempts/max, retry time, lease owner/expiry/token, checkpoint, safe error code | Cancelled/obsolete jobs and expired attempts cannot publish; admission/concurrency are bounded |
| SpeakerIdentity / SpeakerMapping | Session identity, nullable name, run label/participant reference, mapping basis, confidence, actor/revision | Run labels differ from identities; no automatic cross-session voice matching |
| TranscriptRevision | ID/session/parent, input sources, run, state, actor/time/reason, digest | Published immutable snapshot; current pointer changes atomically; final is not verified truth |
| SegmentRevision | Segment ID/revision, predecessors, text/language, nullable interval, timing precision, speaker refs/uncertainty | Split/merge lineage; unknown/multiple speakers valid; no invented word times |
| SourceSpan | Transcript/segment revision, Unicode character start/end, quote/hash, audio mappings | Character span matches immutable text; media precision explicit |
| IndexSnapshot / Chunk | ID, source revision set, chunker spec, chunk text/input hash, source spans, embedding spec, state | Rebuildable; current pointers expose complete compatible snapshots only |
| EmbeddingCacheEntry | Exact input digest, embedding spec, vector/dimensions/normalization | Input includes any title/template; reject nonfinite/wrong-sized/incompatible vectors |
| GeneratedArtifact | Type/status, question/selection, scope/revisions, retrieval snapshot, claims/actions/citations, generation spec, policy/run, coverage/currentness | Private persisted evidence; incomplete notes cannot claim full coverage |

The first slice needs session/source/job records and a small normalized revision fixture, not every future table.

## Adapter outputs

`ASRResult`: run, asset/range and timeline-map version, update identity, text intervals, optional word intervals, observed language, finality and defined uncertainty. Draft updates use `(run_id, hypothesis_id, update_sequence)`; newer updates replace that hypothesis in the UI and a final update seals it. Changed published text requires a new transcript revision. Drafts are excluded from ordinary retrieval/final notes.

`SpeakerInterval`: run, source/map, interval, run-local label and optional confidence/overlap. Assembly maps labels to session identities; no interval proves a real participant name.

`AudioRangeCommitted`: attempt/track/sequence, asset reference, sample/time mapping and durable byte checkpoint. Emit only after the range is recoverable through its manifest. Capture callbacks may fill bounded writer buffers before durability; show the last durable checkpoint and measure crash-loss exposure rather than describing unflushed bytes as saved.

`RetrievedPassage`: snapshot/chunk, session/revision, exact text/source spans, method and ranking signals. No arbitrary file paths or fabricated confidence score.

`GeneratedArtifact.status`: `answered`, `insufficient` or `error`, plus reason; separate `workflow_state` and `currentness` describe building/ready/failed and current/stale/historical. Insufficient reasons distinguish no evidence, inadequate evidence and unresolved conflict; an explanation of conflict may instead be an answered claim citing both sources. Each claim/action has evidence spans. Actions include task, nullable owner, literal due-date text and nullable normalized date/resolution basis. Structural validation does not establish semantic support.

## Publication transactions

| Operation | Preparation | Atomic database effects | Recovery |
|---|---|---|---|
| Accept source | Stream staging, hash/check limits, flush and rename immutable file | Mark available, record metadata, enqueue next job | Reconcile file/DB mismatch; repeated request returns same source/job; another session retains its own source link |
| Publish transcript | Assemble candidate, validate spans/maps and input/parent | Insert revision/segments, conditionally advance current pointer, stale derivatives and enqueue rebuild | Duplicate returns same revision; parent conflict requires review/rebase, never overwrite |
| Publish index | Build against pinned revisions/spec | Verify inputs current; mark ready and swap pointer | Failed/obsolete builds never become current; old snapshot stays historical |
| Publish result | Validate evidence against pinned sources | Store provenance and currentness after checking revision/policy/deletion state | Changed sources produce stale/historical notice or bounded retry |
| Delete session | Mark deleting; fence jobs/reject work | Record cleanup manifest/progress and finally content-free tombstone | Idempotent cleanup resumes; late workers cannot recreate content |

Create a job in the same DB transaction as the state change requiring it. Dedupe by stage, immutable input and config. Automatic retries reuse the job with a new attempt; changed configuration creates new work. Publication checks lease token, job state and input currentness. Heartbeats/deadlines prevent indefinite ownership.

Checkpoints cover only committed output and bind input/config hashes. Reject incompatible resumes. Speech-window overlaps and deterministic merge rules belong to the evaluated adapter; audio processing windows and text retrieval chunks are different units.

## Correction example

An answer cites session `S1`, transcript `R1`, segment revision `G1`, characters `[12, 58)`, and segment-level audio mappings. A correction splits that segment into `G2/G3` in `R2`. Keep `R1/G1` as historical evidence; advance the current pointer to `R2`, stale affected session indexes/results, and rebuild against `R2`. New answers never silently use `R1` evidence as current. Timing-only edits can reuse compatible vectors but must publish new source spans. Explicit audio deletion makes playback unavailable; citations never redirect to different evidence.

## Boundary verification

Use synthetic fixtures and injected failures for duplicate/conflicting keys, stale lease tokens, cancellation races, out-of-order drafts, split/merge corrections, concurrent parent updates, scope isolation, incompatible specs, timestamp gaps and file/DB reconciliation. Fake adapters validate orchestration only. Real adapters additionally require measured compatibility and quality checks.

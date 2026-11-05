# Architecture review: repository evidence and next decisions

Review date: 2026-11-05. Scope: architecture and documentation. Evidence includes project guidelines, requirements, architecture, build plan, ADR 0001, prototype/verification records, Python modules, tests, UI request/citation flow and retrieval evaluation.

## Product understanding

TranscriptLens should turn authorized recordings into a durable workspace: preserved original audio, timestamped and speaker-attributed text, reviewable notes/explicit actions, and answers grounded in selected transcripts with playable evidence. Windows capture and a visible Google Meet bot follow the recorded-file pipeline. Technical meetings/conversations are the initial use case; language/hardware/duration are not yet established. Speech is confirmed local by default with explicit cloud opt-in; this review proposes the same boundary for text processing.

## Confirmed implementation

| Evidence | What it establishes | Limit |
|---|---|---|
| `lens/transcripts.py`, parser tests | UTF-8 TXT/SRT/VTT parsing; supplied speakers/timestamps; sentence/turn chunking targeting 1,200 characters | Speaker strings are source text, not identities. Untimed TXT stays untimed; cues do not establish word alignment or accurate audio |
| `lens/store.py`, storage tests | SQLite original text, normalized-text digest dedupe, versioned chunk IDs, cached embeddings | Only documents/chunks tables. No audio assets, jobs, transcript revisions, correction ledger or persisted generated artifacts |
| `lens/retrieval.py`, evaluation | BM25; exact normalized cosine; rank fusion; synthetic keyword baseline reproduced | Stored JSON vectors, bounded corpus, no ANN/vector service or learned reranker; semantic/hybrid quality not measured live |
| `lens/provider.py`, mocked tests | Optional Gemini HTTP request/response adapter, timeouts and validation | Defaults/configuration are candidates, not proof of current access/compatibility. No real model call or local inference verified in this review |
| `lens/pipeline.py` | Search and optional generation; separate bounded whole-transcript notes; source-ID/normalized-quote checks | Valid quotes do not prove claim support/ownership. Outputs returned to caller rather than persisted with immutable evidence |
| `lens/views.py`, settings and web tests | Loopback reference server, CSRF enforcement, bounded transcript uploads, one-session/all-document search, single-session notes | Synchronous requests; no authentication, arbitrary selected-session set, durable worker or consent-policy enforcement for background work |
| `static/app.js`, routes | Source passages, supplied timestamp display and citation links into displayed passages | No audio element/source route or verified audio seek; timestamp display is not playback |
| Tests and tracked files | 24 tests pass; six deliberately synthetic corpus sessions | No capture, ASR, diarization or Meet participant implementation. Audio upload is deliberately rejected by a test |

The offline rerun reproduced document recall 0.9306, precision 0.4306, MRR 0.9583 and hit rate 1.0000 over 12 synthetic development questions/four retrieved chunks. Labels are document-level, not independent passage relevance or answer support. No generation quality or provider compatibility is inferred.

## Gaps and proposed response

| Gap in the prior design/prototype | Proposed refinement |
|---|---|
| Single session state collapses recording/processing failure | Independent source, capture, job, transcript, index and artifact state; ready transcript remains usable after notes failure |
| Memory queue diagram can imply loss of the only audio copy | Durable source manifest/job backlog; bounded writer buffers and explicit durable checkpoint; inference catches up from saved audio |
| No file/DB atomic commit or restart semantics | Staged source state, flush/rename/DB commit protocol, startup reconciliation and fault-injection gates |
| Coarse timestamps do not define pause/drift/playback | Canonical elapsed timeline, gaps, per-track sample/media maps and precision-aware playback |
| Anonymous labels can be confused with identities | Run-local diarization labels mapped to session-scoped identities; explicit naming/correction and overlap/uncertainty |
| Rechunking deletes old chunks/citations | Immutable transcript evidence spans independent of chunk IDs; stale derived indexes/results and preserve historical resolution |
| Embedding key omits some effective input/task configuration | Complete embedding specification plus exact input hash; atomic compatible snapshots and reusable vectors |
| Empty document ID means all in the prototype | Proposed explicit nonempty session set resolved by the UI; filter scope/revision before ranking |
| Citation checking can be mistaken for correctness | Keep deterministic validation and separate held-out semantic-support/action/abstention evaluation |
| Local-first goal lacks operational cloud policy | Confirmed speech local default; propose the same for text, with per-stage/provider/source opt-in, dispatch recheck and cancellation on revocation |

Avoid premature microservices, brokers, vector services, agent orchestration, cross-session voice identification and a wholesale shell rewrite. Keep simple functions and actual integration adapters. SQLite/exact search remain provisional choices constrained by measured concurrency/corpus size.

## Decisions and open questions

[ADR 0001](decisions/0001-independent-project.md) proposes modular independent components. [ADR 0002](decisions/0002-local-processing-and-provenance.md) records the proposed local application/worker, durable sources, revision and overload choices with alternatives. Both remain proposed architectural baselines, not evidence of implemented integrations.

The speech local/cloud policy is confirmed; its proposed extension to text is part of architecture review. The following also need resolution at their component gates:

1. Representative technical audio: languages/code-switching, terminology, typical/worst duration, speaker counts and noise. No unsupported assumption that all speech is English.
2. Windows CPU/RAM/GPU and acceptable offline turnaround/live lag. Measure before choosing speech runtimes or finite capture budgets.
3. Acceptable ASR, speaker and answer-support error rates; establish held-out labels and freeze numerical targets before accepting adapters.
4. Retention duration, backup location and user expectations for deletion of backups/exports.
5. Whether separate microphone/meeting tracks are available/desired; inspect actual capture routes before choosing a shell/helper.
6. Meet account/access constraints and a currently documented integration route. Do not invent a desktop API or assume browser automation provides reliable media access.

The small first implementation is source acceptance/recovery, described with concrete acceptance scenarios in [BUILD_PLAN.md](BUILD_PLAN.md). It can proceed after architecture review while workload/model decisions remain open. [ARCHITECTURE.md](ARCHITECTURE.md) supplies the component diagram, complete flow, responsibilities, lifecycle/failure handling and privacy boundaries; [CONTRACTS.md](CONTRACTS.md) supplies entities/publication semantics.

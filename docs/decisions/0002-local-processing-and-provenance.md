# ADR 0002: Local processing, durable sources, and immutable evidence

Date: 2026-11-05

Status: Proposed. Local-by-default speech processing with explicit cloud opt-in is confirmed; extending this policy to text processing and the implementation choices below await architecture review.

## Context

The prototype runs text ingestion/retrieval/provider calls synchronously. Rechunking deletes old chunks; it has no transcript revision history, durable audio jobs or playback maps. Future capture must survive slow inference, and corrections must not silently change cited evidence.

## Decision

- Begin with one application codebase, local web UI, one background worker, SQLite metadata/jobs and local audio objects/manifests. Retain the reference shell while verifying boundaries.
- Preserve originals before inference. Durable manifests/jobs form the backlog; finite memory buffers separate capture from processing. Delay live text under inference pressure; visibly interrupt and report gaps under capture/storage pressure.
- Separate capture/source/job/transcript/index/result state. Local publication is idempotent using immutable input/config keys, revisions and lease fencing.
- Use a canonical session timeline with explicit media mappings/gaps, source precision and speaker uncertainty.
- Publish immutable transcript revisions and source-span citations. Corrections invalidate current derivatives; old evidence remains historical until explicit deletion.
- Default each processing stage to local. Cloud transfer needs explicit provider/operation/source opt-in. The existing cloud adapter is neither a verified local alternative nor a complete production policy boundary.
- Retain BM25/bounded exact vectors and compatible embedding reuse. No LLM agent framework is required.

## Alternatives and trade-offs

| Alternative | Trade-off / reason for deferral |
|---|---|
| Synchronous audio web requests | Simpler for tiny text tasks; unsuitable for durable long processing/cancellation |
| Microservices, broker, distributed orchestration | Add consistency/deployment costs before measured need; one worker still requires checkpoints and leases |
| Dedicated vector database / approximate search | Revisit on measured search latency, memory and corpus size; bounded exact search remains inspectable |
| Mutable latest-only transcript/chunks | Smaller schema, but loses historical evidence and correction provenance |
| Cloud-first speech processing | Reduces local resource pressure but conflicts with default and adds data/availability dependencies |
| Browser-only capture / immediate desktop rewrite | Target-machine capture/synchronization spike must establish helper/shell requirements first |
| Meeting bot before recorded-file processing | Entangles platform admission/media failures with unproven speech/storage stages |

## Consequences and reconsideration

SQLite/files simplify deployment but require tested reconciliation, backup/restore and bounded write concurrency. Local models may be slow or unsupported on some hardware; report measured limits and offer cloud only through separately verified opt-in adapters. Immutable history consumes storage until retention is defined.

Revisit deployment/storage when measured contention, backlog or search limits, or shared-user requirements, exceed this baseline. Select speech engines and the Meet route in later ADRs after official-documentation, licensing/attribution and real-flow verification. This record selects no model, platform API, hardware minimum, quality threshold or cloud provider.

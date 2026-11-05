# ADR 0001: Modular application with replaceable integrations

Date: 2026-11-05

Status: Proposed architectural baseline

## Context

The system needs recording, speech recognition, speaker attribution, persistent transcripts, notes, and source-grounded Q&A. These capabilities have different input formats, timing requirements, failure modes, and provider dependencies.

## Decision

Develop an independent application with explicit component boundaries and replaceable adapters. Begin with architecture and contracts, then implement and verify components individually. Use the existing text-transcript prototype as a reference rather than treating its technology choices as final.

Keep original audio, finalized transcript revisions, and derived retrieval indexes distinct. A meeting capture integration must feed the same normalized pipeline used for imported recordings.

## Consequences

The application controls its own data model and user interface. Integration changes should remain localized to adapters, but capture, alignment, lifecycle handling, and recovery still require explicit implementation and verification. More advanced deployment or distribution patterns should be introduced only when measured requirements justify them.

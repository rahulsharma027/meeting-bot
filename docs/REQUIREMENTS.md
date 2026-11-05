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

## Future extensions

Calendar-triggered attendance, email delivery, external task creation, voice responses, and multiple meeting platforms are outside the initial scope. They require separate requirements and authorization boundaries.

# Self-hosted meeting assistant

Status: confirmed product direction and proposed integration pilot, 2026-11-07. Capture, speech recognition, diarization and recording playback are not implemented in TranscriptLens yet.

The [capture-only deployment kit](CAPTURE_PILOT.md) prepares joining/recording checks independently of the text portal. The guest-join attempt failed without a recording. The separate [authenticated deployment](AUTHENTICATED_CAPTURE.md) now restores a dedicated Google account and has joined a real approved Meet call; its host confirmed the bot in the participant list. Its short recording completed, exported with matching checksums and decoded locally with non-silent audio. Listening quality, speech processing and multi-speaker attribution remain separate verification gates.

## Intended experience

The primary workflow is a visible meeting bot that joins Google Meet, captures authorized audio, attributes speech to stable speakers, and saves everything in the existing portal. External transcript preparation is an interim evaluation path. Local or self-hosted capture is confirmed; speech recognition and diarization stay local by default. A third-party hosted capture or speech endpoint is not an implicit fallback.

1. Paste a Meet link into TranscriptLens and request the bot to join.
2. The host admits a visibly named TranscriptLens participant. Recording begins only after the approved recording flow.
3. The portal shows recording state and a provisional, timestamped transcript as processing catches up.
4. Speaker labels persist across turns: Person A → Person B → Person A. A new turn by an existing speaker does not create a new person.
5. After stopping/leaving, retain the recording and finalize the transcript. The meeting remains available for playback, corrections and source-grounded questions.

Example of the intended transcript, using synthetic speech:

```text
00:12  Person A: The parser needs another test.
00:18  Person B: I will add the SRT case.
00:24  Person A: Let us review it tomorrow.
```

Each meeting should have three clear portal views: **Recording**, **Transcript**, and **Ask**. Answers should cite speaker-labelled passages and resolve to the associated recording interval. Do not add working-looking recording controls until a real adapter has passed its acceptance gate.

## Speaker handling

Speech recognition produces text. Speaker attribution determines who spoke during each interval. Prefer reliable participant-linked audio/track information when a capture adapter supplies it. Mixed audio and shared microphones need a separate voice-diarization stage; platform display names alone do not identify every voice in a room. [Capture/diarization methods](https://docs.recall.ai/docs/diarization).

Maintain an internal speaker ID scoped to the meeting. Person A/B are display labels; an optional reviewed name maps to that ID. Preserve unknown speakers, overlap and corrections. Provisional live attribution can change during finalization; corrections must preserve source/revision history. Do not promise immediate or perfect recognition, infer real names from voices, or introduce cross-meeting voice recognition by default.

## Meet integration assessment

Google announced the discontinuation of the Meet Media API developer preview on 2026-10-28, with endpoints scheduled to shut down on 2027-01-15. New signups are closed. It is unsuitable as the foundation for this integration. The [Meet overview](https://developers.google.com/workspace/meet) and [release notes](https://developers.google.com/workspace/meet/release-notes) document this change. The supported [Meet REST API](https://developers.google.com/workspace/meet/api/guides/overview) exposes meeting metadata and generated artifacts; that is a different integration from the requested live joining/capture flow.

Evaluate [Vexa](https://github.com/Vexa-ai/vexa) as a separate self-hosted capture adapter. Its upstream README currently describes version 0.12, Apache-2.0 licensing, Google Meet joining, recordings and speaker-attributed transcripts. It targets Linux/Ubuntu 24.04 with Docker; Windows/WSL2 compatibility must be verified. Capture and speech services are separable. This is a candidate for a pilot, not a validated or installed dependency. Browser-based meeting integration must be checked against actual host/account admission rules and platform changes.

For the first capture check, use its documented [capture-only mode](https://docs.vexa.ai/how-to/deferred-transcription). Do not follow hosted-service quickstart credentials: self-hosted capture does not by itself guarantee local speech processing. If the adapter passes, connect a local speech service through its [custom STT interface](https://docs.vexa.ai/how-to/custom-stt), or process the saved audio in the local worker. Review and pin the exact source revision/images and model licenses before deployment. The upstream bundled speech-service hardware requirements do not establish what will run on the user's Windows machine.

Keep TranscriptLens as the portal and source repository. Use the capture/transcription interface only; Vexa's optional knowledge-agent/workspace features are unnecessary here. Recordings and private transcripts must never be written to the application Git repository. Self-hosting still requires normal network access to Google Meet; it does not make an online meeting an offline operation.

## First integration acceptance gate

Start with one short authorized two-person test meeting. The pilot passes only when all of the following are observed:

- A real bot joins, waits for admission, and appears visibly to participants; denial and join errors are surfaced.
- Captured audio survives stop/restart with its source identity intact. A speech-worker failure does not lose the recording.
- A local speech path produces timed text, with A → B → A mapped consistently. Shared-microphone/overlap uncertainty stays explicit.
- The portal resolves a transcript passage to the right recording interval and can answer a known question from that source.
- Stop/leave ends capture, finalization and source integrity are verified, and processing retries do not duplicate transcript publication.
- Capture/speech data flows are inspected and no hosted speech or capture endpoint is used. Optional existing cloud Q&A remains an explicit user choice.

First prove joining and recording, alongside the durable-source component in [the roadmap](BUILD_PLAN.md). Then prove local transcription/speaker attribution and connect the portal. Live latency, word accuracy, speaker accuracy and hardware use require measurement; they are not established by upstream feature claims or synthetic contract tests.

No live meeting was joined, no capture service/model was installed, and no recording was made during this assessment.

## Deployment prerequisite

The self-hosted pilot requires a working Linux container engine and an explicitly configured local speech endpoint. Verify the target host's runtime compatibility, available CPU/RAM/GPU and storage before deployment. Installed command-line tools alone do not establish that the services can run. No Docker settings were changed and no images were downloaded during this assessment.

# Capture-only meeting pilot

Status: experimental deployment kit, 2026-11-07. Container deployment and authenticated local API access have been verified on a Windows/WSL2 host. The anonymous Meet attempt did not reach the meeting and produced no recording. Admission and usable audio remain unverified. This kit does not add speech recognition, speaker diarization or recording playback to the TranscriptLens portal.

This page describes the guest-only Lite kit. The separate [authenticated capture deployment](AUTHENTICATED_CAPTURE.md) subsequently passed a dedicated-account join and short recording/export test; that result does not make Lite an authenticated-bot deployment.

## Observed pilot result and authentication boundary

The app, PostgreSQL and local object storage became healthy. Storage initialization completed, scoped API-key provisioning worked, and the configured speech endpoint was empty with transcription disabled and the LLM kill switch enabled. Docker Engine 29.9.2, Compose 5.6.1 and Python 3.12.3 were observed on the capture host. The immutable image references were checked directly against the public registry; the initial download completed without changing or bypassing digest verification.

The authorized guest-join request returned a meeting record and reported `awaiting_admission`. The host saw no request. A screenshot from the bot's isolated display showed Google's Meet product landing page, while the requested meeting URL was correctly stored. The attempt was stopped, reached `failed`, and had zero recording records. API lifecycle status alone therefore does not prove that the browser has a live admission request.

A missing Google sign-in has not been established as the sole cause of this redirect. Google documents [guest joins with host admission](https://support.google.com/meet/answer/9303069?hl=en), subject to meeting/account policies. The next evaluation route uses a dedicated bot Google account and [Vexa's supported authenticated-bot flow](https://docs.vexa.ai/authenticated-bots). That flow is supported on Compose; upstream explicitly excludes Lite. Do not treat this Lite kit as a signed-in bot deployment or reuse a personal browser's cookies to work around the boundary. A human must complete the dedicated account's Google sign-in and verification in the provisioning browser.

The separate [dedicated-account sign-in pilot](BOT_SIGNIN.md) prepares that human sign-in through a private SSH-forwarded browser. Its local profile is not yet connected to authenticated meeting capture.

## Run on the capture PC

Use the Windows PC's Ubuntu/WSL2 terminal with Docker Desktop's Linux-engine integration enabled. Python 3.10+ and Docker/Compose must be available inside that terminal. The runtime must be able to pull Linux AMD64 images and reach Google Meet. GPU access is not required for this capture-only stage; it will be checked separately before speech processing.

If using the ZIP kit, extract it and open Ubuntu in its extracted directory. The ZIP contains this guide as `README.md`, the helper under `tools/`, and the configuration under `deploy/`. If using the repository, open its root directory. Then run:

```bash
python3 tools/capture_pilot.py start
```

This checks Docker (Linux engine version 26+), creates local configuration, downloads the pinned browser sandbox profile, pulls the pinned container images and starts the services. The initial image download can be several gigabytes. Wait for:

```text
Capture services are ready. No meeting has been joined and no recording has started.
```

That message confirms the gateway and local bot key are ready; it does not confirm that a meeting can be joined. If startup fails, the helper keeps service state and data intact. Inspect it locally using:

```bash
docker compose --env-file .local/capture-pilot/.env -f deploy/capture-pilot/compose.yaml ps
```

Service logs are available with the same prefix and `logs --tail=100 app`. Logs can contain private meeting details or one-time sign-in links; share a redacted error rather than complete logs or the `.env` file.

## One short test call

Host a short Google Meet test call with two people who have agreed to the recording. Replace the example link below with the actual call's link:

```bash
python3 tools/capture_pilot.py join "https://meet.google.com/abc-defg-hij" --recording-approved
python3 tools/capture_pilot.py status
```

Admit **TranscriptLens Recorder** when it asks to join. The flag records the operator's approval assertion; it does not obtain participant approval on their behalf. The bot is anonymous in this pilot, so a meeting that requires authenticated attendees may refuse it. A successful request is not proof of successful admission or usable audio.

Speak alternately for a few minutes, including a clear A → B → A exchange. Then stop the bot and wait for finalization:

```bash
python3 tools/capture_pilot.py stop
python3 tools/capture_pilot.py status
```

When the status is `completed` (or `failed` with recoverable audio), export it:

```bash
python3 tools/capture_pilot.py download
```

Audio and its byte-count/SHA-256 receipt are saved under `.local/capture-pilot/recordings/`. Listen to confirm both voices were captured. Export requires a terminal meeting state, exactly one recording belonging to that meeting, and a same-origin audio path. It refuses to overwrite saved/partial audio and limits each export to 512 MB and ten minutes of transfer time.

This kit selects one pilot meeting at a time. It saves a receipt before requesting a join and never automatically repeats a failed/ambiguous spawn. Use `status` and `stop` after a network failure; keep the current receipt for diagnosis. A rejected or ambiguous join requires inspection before another pilot is started. Partial exports remain available for inspection; automatic resume is not implemented.

## Local data and shutdown

The helper stores generated configuration and session receipts in `.local/capture-pilot/`, which is ignored by Git. Docker named volumes hold the upstream database, recordings and application state. Container restarts retain those volumes; recovery and backup behavior still need a real deployment test. The pilot uses loopback ports 8056 (API) and 3001 (upstream UI); it does not expose the agent API, mount the Docker socket, or mount personal assistant credentials. Speech endpoints are empty, transcription is explicitly disabled, and the upstream LLM kill switch is enabled.

To stop the services while retaining recordings:

```bash
docker compose --env-file .local/capture-pilot/.env -f deploy/capture-pilot/compose.yaml stop
```

The first pilot is controlled on the capture PC. Access from the laptop and integration with the existing portal require a separate authenticated access path; the current TranscriptLens demo is localhost-only.

## What follows

After a real recording passes review, validate container GPU access and add a separately configured local speech worker. Measure technical-term transcription quality and speaker attribution on the captured sample, then publish timed speaker-labelled text to the portal with recording references. Capture-only mode produces no transcript. The existing text-upload endpoint does not accept this audio export.

## Source, images and attribution

- Upstream: [Vexa](https://github.com/Vexa-ai/vexa), Apache-2.0; source/API review pinned at commit [`6b26f7b921756d6db128d42cd70b4b7046381407`](https://github.com/Vexa-ai/vexa/tree/6b26f7b921756d6db128d42cd70b4b7046381407).
- The helper retrieves the upstream [browser sandbox profile](https://github.com/Vexa-ai/vexa/blob/6b26f7b921756d6db128d42cd70b4b7046381407/core/runtime/src/runtime_kernel/seccomp-userns.json) under the upstream license and checks canonical-file SHA-256 `4ad79f851aabecbb2cdab19f2910ba0f49b923f9ffa71d5bb40422733e540bb7` before use. The downloaded profile stays in ignored local data.
- App: published `vexaai/vexa-lite` v012 manifest, resolved 2026-11-07, pinned to `sha256:9eebb534fdab4079baf11af678968ac8d9679e20ce48db206bcf5a62b85eb538`. Source review and container-manifest pinning are separate; source-to-image correspondence has not been independently established.
- Database: PostgreSQL 17 Alpine (PostgreSQL License), digest pinned in Compose. Storage: VersityGW 1.10.0 (Apache-2.0), digest pinned in Compose. No speech model or speech-model license is included in this stage.
- Relevant upstream guides: [Lite deployment](https://docs.vexa.ai/deployment-lite), [capture-only mode](https://docs.vexa.ai/how-to/deferred-transcription), [recordings](https://docs.vexa.ai/how-to/recordings).

The helper's synthetic local-HTTP tests cover approval and URL validation, capture-only requests, stop/export contracts, recording scope, redirect refusal, retained partial downloads, no-overwrite behavior, credential-safe output and atomic receipt replacement. They establish client behavior only. No live capture, Windows/WSL compatibility, audio quality, speaker accuracy or portal playback claim follows from these tests.

# Authenticated capture pilot

This deployment connects a confirmed dedicated Google-account session to a self-hosted, capture-only Meet bot. It is a minimal Compose surface based on upstream Vexa v0.12.28, separate from the guest-only Lite pilot. Meeting admission and usable recording must still be tested on a real, approved call; a healthy API is insufficient.

## Provisioning and startup

Complete [dedicated-account sign-in](BOT_SIGNIN.md) first. Its private Docker volume must exist on the same capture host. On that host, from the repository root:

```bash
python3 deploy/authenticated-capture/prepare.py
python3 deploy/authenticated-capture/build_browser.py
docker compose --env-file .local/authenticated-capture/.env \
  -f deploy/authenticated-capture/compose.yaml up -d --wait
docker compose --env-file .local/authenticated-capture/.env \
  -f deploy/authenticated-capture/compose.yaml run --rm --no-deps session-export
docker compose --env-file .local/authenticated-capture/.env \
  -f deploy/authenticated-capture/compose.yaml run --rm --no-deps session-verify
```

Preparation generates private local secrets once and preserves them on subsequent runs. It downloads the upstream storage initializer from source revision `f1a62fbbdfd2c98cb162582d82c31fe8102acc89`, verifies SHA-256 `394f61caa96dd202e11da51192792d51848391f516dadbd840623554a02da5c3`, and mounts that verified file read-only. The initializer is [upstream Apache-2.0 source](https://github.com/Vexa-ai/vexa/blob/f1a62fbbdfd2c98cb162582d82c31fe8102acc89/deploy/storage/storage_init.py); [license](https://github.com/Vexa-ai/vexa/blob/f1a62fbbdfd2c98cb162582d82c31fe8102acc89/LICENSE). A digest mismatch refuses preparation.

Storage initialization creates a userdata account distinct from the recording-store root account. Actual S3 operations must prove that this account can list/read/write/delete its own prefix while being denied recordings, whole-bucket listings and objects outside the prefix. Meeting-api waits for that check to succeed.

Session export mounts the confirmed sign-in profile read-only and uses the same upstream auth-essential subset exporter as the provisioning CLI. Only local storage receives it. Export checks that the required `Local State` and `Default/Cookies` objects exist with nonzero lengths before writing its private success receipt. Successful repeated exports preserve the existing stored session: an old initial profile must not overwrite a session refreshed by meeting use. Source profile data remains intact after failures. A partial export failure still requires inspection before reuse.

### Pinned browser continuity fix

The first authenticated retry still opened an incognito browser and redirected to Google's public Meet product page. Source inspection established that this release merges the guest join flags, including `--incognito`, into authenticated launches. The stopped retry produced no usable recording. Its API status incorrectly remained `joining` after the bot reported `needs_help`; the lifecycle API rejected that transition. API state alone must therefore not be used to claim admission.

`Dockerfile.bot` derives from the pinned upstream bot and applies one guarded replacement: exclude `--incognito` when the invocation is authenticated. Guest launches retain their original flags. The patch checks the original compiled file's SHA-256, requires exactly one matching launch site, evaluates both modes and runs a JavaScript syntax check. It changes no Google login, account, certificate or meeting admission checks. The build helper selects the resulting immutable local image ID in private configuration and preserves other secrets. A changed upstream file refuses the patch rather than applying it speculatively.

`session-verify` uses the actual patched bot launch path to restore the local session and run upstream's logged-in validation without joining or recording a meeting. Only a verified profile is written back through clean teardown. A failed verification closes the browser without overwriting the stored session. Keep its raw browser output private; the success marker reports only that authentication was verified, not an account identity.

The API key is a separate local operator credential, unrelated to the Google account. Provision an upstream user with a one-bot limit and a `bot,tx` key through admin-api's internal container connection. Keep its token in private host storage, never in a URL, browser bundle, terminal output shared with others, or Git. The current pilot's key provisioning was performed privately over verified SSH; portal controls are not yet implemented.

## Network, credentials and resources

- Gateway: capture-host loopback `127.0.0.1:18056`; authenticated API access only. Its separate edge network permits Docker to publish that loopback port.
- Database, admin-api and runtime: private control network; no host ports. Bot containers do not join this network.
- Bots: separate network with meeting-api callbacks, Valkey and local object storage; outbound access is required for Google Meet.
- Runtime: Docker socket access is needed to create bot containers. This grants host-level container control, so the runtime API remains unpublished and isolated from bot containers. No personal assistant/browser credential directories are mounted.
- Speech and agents: transcription disabled, speech URL/token empty, no agent services or worker image, no model credentials, LLM kill switch enabled. This stage produces recordings only.
- Persistence: separate database, storage, cache and export-state volumes; the earlier Lite volumes are retained. The saved Google session is credential material stored locally without an additional encryption layer. Docker-host administrators can access it.

Service memory limits total under 4 GB, with one additional browser workload. Upstream v0.12.28's Docker runtime does not enforce memory limits on spawned bots. Do not interpret the Compose service limits as a bot-memory guarantee; this is a single-user, one-meeting pilot whose live memory use still needs observation. Multi-user isolation, backup/restore, rotation and crash recovery are not verified by this setup.

## Controlled meeting test

Use a short call whose participants have agreed to recording. Persist a private meeting receipt before `POST /bots`; send `platform=google_meet`, the approved meeting code, `recording_enabled=true` and `transcribe_enabled=false`. Deployment-level `BOT_AUTHENTICATED=true` supplies the saved session. Do not auto-repeat an ambiguous join. Check both API state and the host's participant list. The signed-in Google account's identity may be displayed rather than the guest name.

Capture a short alternating-speaker sample, stop with `DELETE /bots/google_meet/{code}`, wait for terminal state, then export the meeting-owned audio and verify its bytes and audible content. Preserve partial output and any failed-attempt receipt. Do not claim transcription or diarization from this capture test.

Stop services with the same Compose prefix and `stop`; keep volumes. Browser sessions refresh through clean bot teardown using upstream's scoped write-back flow. A hard kill can leave the last durable session unchanged. See [upstream authenticated-bot behavior and limits](https://docs.vexa.ai/authenticated-bots).

## Observed setup: 2026-11-07

The dedicated-account provisioning container exited zero and its compatible sign-in success receipt was present. No cookie values, passwords or verification codes were read into the development session. Seven long-running authenticated-capture services became healthy, and storage initialization passed its real scoped-access checks. Thirteen auth-essential items were exported locally; mandatory-object metadata checks passed. Gateway access using the private scoped API key succeeded with zero bots before the approved retry. All service and bot images are digest-pinned; registry manifest bytes were independently checked.

The guarded derived image subsequently passed real Google logged-in validation after restoring the stored session through the actual bot launch path. That verification joined no meeting and made no recording. A subsequent explicitly approved retry reached `active`, and the host confirmed the bot's presence in the meeting. The browser used approximately 719 MiB of memory in one snapshot; that is not a resource benchmark.

The controlled test was stopped and both meeting and audio recording reached `completed`. The meeting-owned WebM export contained 1,483,612 bytes; its SHA-256 matched after encrypted transfer to the laptop. Local Chrome decoding, with network requests blocked, produced 120.18 seconds of stereo audio at 48 kHz with non-silent samples. No cloud speech provider or ASR was used. The operator reported that only one person spoke, so this sample establishes no multi-speaker attribution result. Private audio and checksums remain outside Git. Listening quality, recovery after a full service restart, local speech, speaker attribution and portal integration remain unverified.

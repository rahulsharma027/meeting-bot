# Dedicated Google-account sign-in pilot

This is a bounded provisioning step, separate from meeting capture. It runs the upstream Google sign-in CLI in an isolated browser on the capture host. A human enters the dedicated bot account's credentials directly on Google's page. It never joins a meeting, records audio, configures a speech provider or mounts personal browser/assistant credentials.

## Runtime and private storage

The browser image is upstream `vexaai/vexa-bot:v0.12.28`, pinned to `sha256:e2398bfac7fa8671c209e996bc6451598b58438c851956ec050a0300f5a5354b`. The public registry digest was independently checked against the manifest bytes on 2026-11-07. The corresponding source tag resolves to `f1a62fbbdfd2c98cb162582d82c31fe8102acc89`. See [upstream authenticated-bot documentation](https://docs.vexa.ai/authenticated-bots).

The profile is retained in the capture host's `transcriptlens-bot-signin_profile` Docker volume, with a private directory and restrictive file creation permissions. **The saved browser profile is a credential.** It must not be copied to Git, a shared ZIP, a chat, screenshots or logs. This first step uses the upstream CLI's local-profile mode; the scoped userdata-store export and authenticated capture deployment are still separate dependencies. Lite does not support authenticated bots, and this step does not change that limitation.

The noVNC service is published only on capture-host loopback port 16080. VNC has an ephemeral password, X11 has a private authorization cookie, and both disappear when provisioning ends. The password is supplied inside the temporary private page, never in a URL. Access from a laptop uses SSH forwarding; do not expose the port publicly or forward it to the LAN. Anyone with access to the tunnel's loopback page can control this isolated browser during sign-in.

## Start and use

Run with Docker/Compose on the Linux capture host. Set `SECCOMP_PROFILE` to the verified browser sandbox profile used by the capture pilot. From the repository root:

```bash
SECCOMP_PROFILE=/absolute/path/to/seccomp-userns.json \
  docker compose -f deploy/bot-signin/compose.yaml up -d --wait
```

On the laptop, forward the private port using its configured SSH host alias:

```bash
ssh -N -T -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:16080:127.0.0.1:16080 transcriptlens-pc
```

Open `http://127.0.0.1:16080/index.html` in the laptop's browser. Enter the dedicated account's email, password and any verification codes only on Google's page inside that view. No sign-in screenshots or browser contents should be inspected by automation once the human starts entering credentials. Follow Google's account checks normally; a rejected login is a failed test, not a reason to bypass those checks.

Provisioning waits up to twenty minutes. The browser closes automatically after upstream logged-in validation succeeds. Exit code zero plus `/profile/login-confirmed.json` records that validation; it does not prove that a future meeting admits the account. A failed or timed-out attempt writes no success receipt. Browser output is suppressed to avoid leaking account information. Do not read or print profile contents when checking the receipt. A confirmed session prevents this helper from automatically reopening sign-in.

Stop the provisioning service with the same Compose prefix and `stop`; close the SSH tunnel when it is no longer needed. Keep the profile volume for the next integration step. No automatic deletion is performed.

## Observed verification

On 2026-11-07 the pinned image was pulled on the Windows/WSL2 capture host. Required display and login components were present, Compose validation passed, and the container became healthy. An isolated laptop browser connected over the SSH tunnel; noVNC delivered the initial Google sign-in screen with no JavaScript errors or failed client asset requests. No account credentials had been entered during that check. The display was adjusted to the upstream browser's 1920×1080 window to keep the complete sign-in form visible.

The human subsequently completed Google sign-in. The container exited zero and its compatible success receipt was verified without reading the profile contents. The private sign-in SSH tunnel was closed. The confirmed profile was then connected to the [authenticated capture pilot](AUTHENTICATED_CAPTURE.md), whose scoped storage checks and local export succeeded. Authenticated Meet admission and usable recording remain separate verification gates.

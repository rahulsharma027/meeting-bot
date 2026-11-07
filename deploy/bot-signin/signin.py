"""Expose one isolated upstream provisioning browser through a loopback SSH tunnel.

The saved Google profile is a credential. It stays in the capture host's private
Docker volume. This process never reads cookies or prints browser/login output.
"""
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import subprocess
import tempfile
import time


def wait_port(port, process):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("A sign-in display service exited during startup")
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError("The sign-in display did not become ready")


def main():
    os.umask(0o077)
    profile = Path('/profile')
    profile.mkdir(exist_ok=True)
    profile.chmod(0o700)
    confirmed = profile / 'login-confirmed.json'
    if confirmed.exists():
        print('A confirmed session already exists; sign-in was not restarted.', flush=True)
        return 2
    children = []

    def stop(_signal, _frame):
        raise InterruptedError('Sign-in stopped by operator')

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    with tempfile.TemporaryDirectory(prefix='transcriptlens-signin-') as private:
        work = Path(private)
        env = dict(os.environ, XAUTHORITY=str(work / 'Xauthority'))
        cookie = secrets.token_hex(16)
        subprocess.run(['xauth', '-f', env['XAUTHORITY'], 'add', ':99', '.', cookie],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        password = secrets.token_urlsafe(6)  # VNC authentication uses eight characters.
        subprocess.run(['x11vnc', '-storepasswd', password, str(work / 'vnc.pass')],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        web = work / 'web'
        shutil.copytree('/usr/share/novnc', web)
        # The temporary credential is delivered in the private page, never a URL.
        # Host port binding is loopback-only; remote access must use SSH forwarding.
        (web / 'index.html').write_text('''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TranscriptLens · Bot account sign-in</title>
<style>body{margin:0;background:#edf3f0;color:#183b37;font:15px system-ui}
header{padding:14px 20px}p{margin:4px 0}#screen{height:calc(100vh - 100px);background:#182321}
#status{font-size:13px}a{color:inherit}</style>
<header><strong>Sign in with your dedicated bot Google account</strong>
<p>Enter passwords and verification codes only inside Google's page below. No meeting is being recorded.</p>
<p id="status">Connecting to your gaming PC…</p></header><div id="screen"></div>
<script type="module">
import RFB from './core/rfb.js';
const status = document.getElementById('status');
const rfb = new RFB(document.getElementById('screen'),
  `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/websockify`,
  {credentials:{password:''' + json.dumps(password) + '''}});
rfb.scaleViewport = true; rfb.resizeSession = false;
rfb.addEventListener('connect', () => status.textContent = 'Connected · Sign-in closes automatically after Google confirms it.');
rfb.addEventListener('disconnect', () => status.textContent = 'Browser closed. Return to TranscriptLens so the saved-session status can be checked.');
rfb.addEventListener('securityfailure', () => status.textContent = 'Connection refused. Return to TranscriptLens for a connection check.');
</script></html>''', encoding='utf-8')

        def spawn(args):
            child = subprocess.Popen(args, env=env, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
            children.append(child)
            return child

        try:
            display = spawn(['Xvfb', ':99', '-screen', '0', '1920x1080x24',
                             '-auth', env['XAUTHORITY'], '-nolisten', 'tcp'])
            for _ in range(50):
                if display.poll() is not None:
                    raise RuntimeError('The isolated display exited')
                if Path('/tmp/.X11-unix/X99').exists():
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError('The isolated display did not start')
            vnc = spawn(['x11vnc', '-display', ':99', '-localhost', '-rfbport', '5900',
                         '-forever', '-shared', '-rfbauth', str(work / 'vnc.pass')])
            wait_port(5900, vnc)
            websock = spawn(['websockify', '--web', str(web), '6080', 'localhost:5900'])
            wait_port(6080, websock)
            cli = spawn(['node', '/app/core/meetings/modules/remote-browser/dist/provision-cli.js'])
            print('Private sign-in browser ready; no meeting has been joined.', flush=True)
            result = cli.wait(timeout=1230)
            if result != 0:
                print('Google sign-in was not confirmed. No success receipt was written.', flush=True)
                return 1
            # The upstream CLI exits zero only after its logged-in validation passes.
            with confirmed.open('x', encoding='utf-8') as receipt:
                json.dump({'platform': 'google', 'validated_at_unix': int(time.time()),
                           'image_version': 'v0.12.28', 'storage': 'local-profile-only'}, receipt)
            print('Google sign-in confirmed. Session retained on the capture PC.', flush=True)
            return 0
        finally:
            for child in reversed(children):
                if child.poll() is None:
                    child.terminate()
            for child in reversed(children):
                try:
                    child.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError, InterruptedError) as exc:
        print(f'Sign-in setup stopped ({type(exc).__name__}); no meeting was joined.', flush=True)
        raise SystemExit(1)

"""Experimental local Vexa capture pilot; Python standard library only.

No speech/model endpoint, remote API, assistant credential mount or automatic join.
See docs/CAPTURE_PILOT.md for scope, source attribution and verification limits.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / '.local' / 'capture-pilot'
COMPOSE = ROOT / 'deploy' / 'capture-pilot' / 'compose.yaml'
API = 'http://127.0.0.1:8056'
UPSTREAM_REVISION = '6b26f7b921756d6db128d42cd70b4b7046381407'
PROFILE_URL = f'https://raw.githubusercontent.com/Vexa-ai/vexa/{UPSTREAM_REVISION}/core/runtime/src/runtime_kernel/seccomp-userns.json'
PROFILE_SHA256 = '4ad79f851aabecbb2cdab19f2910ba0f49b923f9ffa71d5bb40422733e540bb7'
MAX_JSON = 2_000_000
MAX_RECORDING = 512 * 1024 * 1024


class PilotError(Exception):
    """Safe operational message; never includes credentials or private API bodies."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward the local API key to a different origin.


def write_private(path, content, *, replace=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if replace:
        descriptor, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    else:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    if replace:
        os.replace(temporary, path)


def prepare():
    DATA.mkdir(parents=True, exist_ok=True)
    env = DATA / '.env'
    profile = DATA / 'seccomp-userns.json'
    if profile.exists():
        content = profile.read_bytes()
    else:
        try:
            with urllib.request.urlopen(PROFILE_URL, timeout=30) as response:
                content = response.read(100_001)
        except (OSError, urllib.error.URLError) as exc:
            raise PilotError('Could not fetch the pinned browser sandbox profile.') from exc
    if hashlib.sha256(content).hexdigest() != PROFILE_SHA256:
        raise PilotError('Browser sandbox profile checksum mismatch; preparation stopped.')
    if not profile.exists():
        write_private(profile, content.decode('utf-8'))
    if not env.exists():
        values = {key: secrets.token_hex(32) for key in (
            'DB_PASSWORD', 'ADMIN_TOKEN', 'STORAGE_ACCESS_KEY', 'STORAGE_SECRET_KEY')}
        values['SECCOMP_PROFILE'] = json.dumps(profile.resolve().as_posix())
        write_private(env, ''.join(f'{key}={value}\n' for key, value in values.items()))
    print('Pilot configuration ready. Existing credentials and data were preserved.')


def run(arguments, *, timeout=60):
    try:
        environment = os.environ.copy()
        if arguments[:2] == ['docker', 'compose']:
            for key in ('DB_PASSWORD', 'ADMIN_TOKEN', 'STORAGE_ACCESS_KEY', 'STORAGE_SECRET_KEY', 'SECCOMP_PROFILE'):
                environment.pop(key, None)  # Use this pilot's .env, not another project's shell credentials.
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=timeout, check=False, env=environment)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PilotError('Docker command unavailable or timed out. Start Docker Desktop with its Linux engine.') from exc
    if result.returncode:
        raise PilotError('Docker command failed. Check Docker Desktop; local service logs can diagnose startup errors.')
    return result.stdout


def compose(*arguments, timeout=60):
    return run(['docker', 'compose', '--project-name', 'transcriptlens-capture-pilot', '--env-file', str(DATA / '.env'), '-f', str(COMPOSE), *arguments], timeout=timeout)


def check():
    host = os.environ.get('DOCKER_HOST', '')
    if host and not host.startswith(('unix://', 'npipe://')):
        raise PilotError('Run the kit on the capture PC with a local Docker socket, not a remote Docker endpoint.')
    contexts = json.loads(run(['docker', 'context', 'inspect']))
    host = contexts[0].get('Endpoints', {}).get('docker', {}).get('Host', '')
    if not host.startswith(('unix://', 'npipe://')):
        raise PilotError('Select the local Docker Desktop Linux context before starting the capture pilot.')
    info = json.loads(run(['docker', 'info', '--format', '{{json .}}']))
    if info.get('OSType') != 'linux' or int(str(info.get('ServerVersion', '0')).split('.')[0]) < 26:
        raise PilotError('The pilot requires a Linux Docker engine, version 26 or newer.')
    run(['docker', 'compose', 'version'])
    print('Linux Docker engine and Compose are available. This capture-only pilot does not use the GPU yet.')


def api_key():
    text = compose('exec', '-T', 'app', 'cat', '/run/vexa/key.env')
    for line in text.splitlines():
        if line.startswith('VEXA_BOT_API_KEY='):
            key = line.partition('=')[2].strip()
            if key and '\r' not in key and '\n' not in key:
                return key
    raise PilotError('The local bot API key is not ready yet. Wait for startup, then run status again.')


def open_api(path, *, method='GET', payload=None, key=None, timeout=90):
    if not path.startswith('/') or path.startswith('//') or '\\' in path:
        raise PilotError('Invalid local API path.')
    headers = {'X-API-Key': key or api_key()}
    body = None
    if payload is not None:
        headers['Content-Type'] = 'application/json'
        body = json.dumps(payload).encode('utf-8')
    request = urllib.request.Request(API + path, data=body, method=method, headers=headers)
    try:
        return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect()).open(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        code = exc.code
        exc.close()
        raise PilotError(f'Local bot API returned HTTP {code}. No automatic retry was attempted.') from exc
    except (OSError, urllib.error.URLError) as exc:
        raise PilotError('Local bot API did not respond. Use status before repeating a join request.') from exc


def api_json(path, **kwargs):
    with open_api(path, **kwargs) as response:
        content = response.read(MAX_JSON + 1)
    if len(content) > MAX_JSON:
        raise PilotError('Local API response exceeded the pilot size limit.')
    try:
        result = json.loads(content)
    except (ValueError, UnicodeError) as exc:
        raise PilotError('Local API returned unreadable JSON.') from exc
    if not isinstance(result, dict):
        raise PilotError('Local API returned an unexpected response shape.')
    return result


def start():
    check()
    prepare()
    compose('config', '--quiet')
    print('Pulling pinned capture images. The first download can take several minutes.', flush=True)
    compose('pull', timeout=1200)
    compose('up', '-d', timeout=240)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        try:
            api_json('/health', key='startup-check', timeout=5)
            api_key()
            print('Capture services are ready. No meeting has been joined and no recording has started.')
            return
        except PilotError:
            time.sleep(2)
    raise PilotError('Startup has not passed its health/key checks. Services and volumes were left intact for diagnosis.')


def meeting_code(value):
    url = urllib.parse.urlsplit(value)
    if url.scheme != 'https' or url.netloc.lower() != 'meet.google.com' or not re.fullmatch(r'/[a-z]{3}-[a-z]{4}-[a-z]{3}/?', url.path):
        raise PilotError('Use a Google Meet link with a three-part meeting code.')
    return url.path.strip('/')


def current():
    try:
        state = json.loads((DATA / 'current.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise PilotError('No pilot meeting is selected. Join an approved test meeting first.') from exc
    if (state.get('version') != 1 or state.get('recording_approved') is not True or
            not re.fullmatch(r'[0-9a-f]{16}', str(state.get('receipt', ''))) or
            not re.fullmatch(r'[a-z]{3}-[a-z]{4}-[a-z]{3}', str(state.get('code', '')))):
        raise PilotError('Saved pilot meeting is invalid.')
    return state


def save_session(state):
    content = json.dumps(state, indent=2) + '\n'
    write_private(DATA / 'current.json', content, replace=True)
    write_private(DATA / 'sessions' / f'{state["receipt"]}.json', content, replace=True)


def join(url, approved=False):
    code = meeting_code(url)
    if not approved:
        raise PilotError('Join requires --recording-approved for a test call whose participants agreed to recording.')
    if (DATA / 'current.json').exists():
        raise PilotError('A pilot meeting is already selected. Use status, stop and download before starting a separate pilot.')
    key = api_key()
    active = api_json('/bots/status', key=key).get('running', [])
    if active:
        raise PilotError('Another bot is running. This pilot supports one meeting at a time.')
    state = {'version': 1, 'code': code, 'id': None, 'receipt': secrets.token_hex(8), 'recording_approved': True}
    save_session(state)  # Persist before spawning: a timeout must not encourage a duplicate join.
    result = api_json('/bots', method='POST', key=key, payload={
        'platform': 'google_meet', 'native_meeting_id': code,
        'bot_name': 'TranscriptLens Recorder', 'recording_enabled': True, 'transcribe_enabled': False,
    })
    identifier = result.get('id')
    if type(identifier) is not int or identifier <= 0:
        raise PilotError('Join response has no meeting id. Use status; the request may already have been accepted.')
    state['id'] = identifier
    save_session(state)
    print('Join requested. Admit the visible TranscriptLens Recorder participant in the test meeting.')
    print('Run status to confirm admission; a successful request does not prove recording works.')


def resolve_session():
    state = current()
    if state.get('id') is None:
        running = api_json('/bots/status').get('running', [])
        match = next((row for row in running if row.get('platform') == 'google_meet' and
                      (row.get('platform_specific_id') or row.get('native_meeting_id')) == state['code']), None)
        if not match or type(match.get('id')) is not int:
            raise PilotError('The join outcome is unknown and no matching active bot was found. Inspect the local bot service before retrying.')
        state['id'] = match['id']
        save_session(state)
    if type(state['id']) is not int or state['id'] <= 0:
        raise PilotError('Saved meeting id is invalid.')
    return state


def status():
    state = resolve_session()
    data = api_json(f'/meetings/{state["id"]}')
    print(f'Meeting {state["id"]}: {data.get("status", "not reported")}')
    print('Capture only: local speech processing and portal integration are the next stages.')


def stop():
    state = current()
    api_json(f'/bots/google_meet/{state["code"]}', method='DELETE')
    print('Stop requested. Run status until the meeting is terminal before downloading audio.')


def download():
    state = resolve_session()
    data = api_json(f'/meetings/{state["id"]}')
    if data.get('status') not in {'completed', 'failed'}:
        raise PilotError('Wait until capture has stopped and the meeting status is completed or failed.')
    items = api_json(f'/recordings?meeting_id={state["id"]}&limit=50').get('recordings', [])
    if len(items) != 1:
        raise PilotError('Expected one pilot recording. Inspect the local recording list before exporting.')
    rec = items[0]
    if rec.get('meeting_id') != state['id']:
        raise PilotError('Recording does not belong to the selected pilot meeting.')
    rec_id = rec.get('id')
    audio = next((media for media in rec.get('media_files', []) if media.get('type') == 'audio'), None)
    if type(rec_id) is not int or rec_id <= 0 or not audio or audio.get('format') not in {'webm', 'wav', 'ogg', 'mp3', 'm4a', 'mp4', 'opus', 'flac'}:
        raise PilotError('No supported audio recording is available yet.')
    master = api_json(f'/recordings/{rec_id}/master?type=audio')
    path = master.get('raw_url', '')
    if not re.fullmatch(rf'/recordings/{rec_id}/media/[0-9]+/raw\?type=audio', path):
        raise PilotError('The recording API returned an unexpected media path; export stopped.')
    target = DATA / 'recordings' / f'{rec_id}.{audio["format"]}'
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + '.part')
    if target.exists() or partial.exists():
        raise PilotError('An export or partial export already exists. Existing audio will not be overwritten.')
    digest, size = hashlib.sha256(), 0
    deadline = time.monotonic() + 600
    with open_api(path) as response, partial.open('xb') as output:
        while block := response.read(1024 * 1024):
            size += len(block)
            if size > MAX_RECORDING or time.monotonic() > deadline:
                raise PilotError('Recording exceeds the pilot size/time limit. Partial bytes were retained.')
            output.write(block)
            digest.update(block)
        expected = response.headers.get('Content-Length')
        if not size or (expected is not None and size != int(expected)):
            raise PilotError('Recording download was incomplete. Partial bytes were retained.')
        output.flush()
        os.fsync(output.fileno())
    partial.rename(target)
    receipt = {'meeting_id': state['id'], 'recording_id': rec_id, 'bytes': size, 'sha256': digest.hexdigest()}
    write_private(target.with_suffix(target.suffix + '.json'), json.dumps(receipt, indent=2) + '\n')
    print(f'Audio saved under .local/capture-pilot/recordings/{target.name} ({size} bytes).')
    print('Listen to verify both speakers. This export is not yet imported into the TranscriptLens portal.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'check', 'start', 'join', 'status', 'stop', 'download'])
    parser.add_argument('meeting_url', nargs='?')
    parser.add_argument('--recording-approved', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.action == 'join':
            if not args.meeting_url:
                parser.error('join requires a meeting URL')
            join(args.meeting_url, args.recording_approved)
        else:
            if args.meeting_url or args.recording_approved:
                parser.error('meeting URL and recording approval apply only to join')
            actions = {'prepare': prepare, 'check': check, 'start': start, 'status': status, 'stop': stop, 'download': download}
            actions[args.action]()
    except (PilotError, OSError, ValueError, subprocess.SubprocessError) as exc:
        if isinstance(exc, PilotError):
            print(f'Pilot: {exc}', file=sys.stderr)
        else:
            print('Pilot: operation failed. Local files and service state were retained for diagnosis.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

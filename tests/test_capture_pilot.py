"""Synthetic HTTP contracts only: no containers, speech models or real meetings."""
from contextlib import redirect_stdout
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from tools import capture_pilot as pilot


class CapturePilotTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.data = Path(self.folder.name)
        self.requests = []
        self.post_failure = False
        self.foreign_recording = False
        self.offsite_media = False
        self.raw = b'synthetic recording bytes'
        self.stopped = False
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def reply(self, body, status=200, raw=False):
                data = body if raw else json.dumps(body).encode()
                self.send_response(status)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                owner.requests.append(('GET', self.path, self.headers.get('X-API-Key')))
                if self.path == '/bots/status':
                    self.reply({'running': []})
                elif self.path == '/meetings/42':
                    self.reply({'id': 42, 'status': 'completed' if owner.stopped else 'active'})
                elif self.path.startswith('/recordings?'):
                    self.reply({'recordings': [{'id': 99, 'meeting_id': 43 if owner.foreign_recording else 42,
                                               'media_files': [{'type': 'audio', 'format': 'webm'}]}]})
                elif self.path == '/recordings/99/master?type=audio':
                    self.reply({'raw_url': 'https://example.invalid/private' if owner.offsite_media else '/recordings/99/media/5/raw?type=audio'})
                elif self.path == '/recordings/99/media/5/raw?type=audio':
                    self.reply(owner.raw, raw=True)
                elif self.path == '/redirect':
                    self.send_response(302)
                    self.send_header('Location', 'https://example.invalid/private')
                    self.end_headers()
                else:
                    self.reply({'error': 'synthetic unknown route'}, 404)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                owner.requests.append(('POST', self.path, body))
                self.reply({'id': 42, 'status': 'joining'}, 503 if owner.post_failure else 201)

            def do_DELETE(self):
                owner.requests.append(('DELETE', self.path, None))
                owner.stopped = True
                self.reply({'status': 'stopping'})

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.patches = [patch.object(pilot, 'DATA', self.data), patch.object(pilot, 'API', f'http://127.0.0.1:{self.server.server_port}'),
                        patch.object(pilot, 'api_key', return_value='synthetic-local-key')]
        for item in self.patches:
            item.start()
        self.output = io.StringIO()
        self.capture = redirect_stdout(self.output)
        self.capture.__enter__()

    def tearDown(self):
        self.capture.__exit__(None, None, None)
        for item in reversed(self.patches):
            item.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.folder.cleanup()

    def join(self):
        pilot.join('https://meet.google.com/abc-defg-hij', approved=True)

    def test_recording_requires_approval_and_valid_meet_url(self):
        with self.assertRaises(pilot.PilotError):
            pilot.join('https://meet.google.com/abc-defg-hij')
        for value in ['https://example.com/abc-defg-hij', 'https://meet.google.com@evil.test/abc-defg-hij',
                      'http://meet.google.com/abc-defg-hij', 'https://meet.google.com/../../private']:
            with self.assertRaises(pilot.PilotError):
                pilot.join(value, approved=True)
        self.assertEqual(self.requests, [])

    def test_join_stop_and_export_preserve_capture_and_scope(self):
        self.join()
        payload = next(row[2] for row in self.requests if row[0] == 'POST')
        self.assertEqual(payload, {'platform': 'google_meet', 'native_meeting_id': 'abc-defg-hij',
                                  'bot_name': 'TranscriptLens Recorder', 'recording_enabled': True, 'transcribe_enabled': False})
        self.assertEqual(pilot.current()['id'], 42)
        with self.assertRaises(pilot.PilotError):
            pilot.download()  # A running recording must not be exported as final.
        pilot.status()
        pilot.stop()
        self.assertIn(('DELETE', '/bots/google_meet/abc-defg-hij', None), self.requests)
        pilot.download()
        path = self.data / 'recordings' / '99.webm'
        self.assertEqual(path.read_bytes(), self.raw)
        receipt = json.loads(path.with_suffix('.webm.json').read_text())
        self.assertEqual(receipt, {'meeting_id': 42, 'recording_id': 99, 'bytes': len(self.raw), 'sha256': hashlib.sha256(self.raw).hexdigest()})
        with self.assertRaises(pilot.PilotError):
            pilot.download()
        self.assertEqual(path.read_bytes(), self.raw)
        self.assertNotIn('synthetic-local-key', self.output.getvalue())

    def test_ambiguous_join_failure_keeps_receipt_and_never_replays(self):
        self.post_failure = True
        with self.assertRaises(pilot.PilotError):
            self.join()
        self.assertIsNone(pilot.current()['id'])
        self.assertEqual(len(list((self.data / 'sessions').glob('*.json'))), 1)
        with self.assertRaises(pilot.PilotError):
            self.join()
        self.assertEqual(sum(row[0] == 'POST' for row in self.requests), 1)

    def test_foreign_recording_and_offsite_media_are_refused(self):
        self.join()
        pilot.stop()
        self.foreign_recording = True
        with self.assertRaisesRegex(pilot.PilotError, 'does not belong'):
            pilot.download()
        self.foreign_recording = False
        self.offsite_media = True
        with self.assertRaisesRegex(pilot.PilotError, 'unexpected media path'):
            pilot.download()
        self.assertFalse((self.data / 'recordings').exists())

    def test_redirect_never_forwards_key(self):
        with self.assertRaisesRegex(pilot.PilotError, 'HTTP 302'):
            pilot.api_json('/redirect')
        with self.assertRaises(pilot.PilotError):
            pilot.api_json('//example.invalid/private')

    def test_failed_export_keeps_partial_bytes_and_refuses_overwrite(self):
        self.join()
        pilot.stop()
        self.raw = b'x' * (1024 * 1024 + 20)
        with patch.object(pilot, 'MAX_RECORDING', 1024 * 1024):
            with self.assertRaises(pilot.PilotError):
                pilot.download()
        partial = self.data / 'recordings' / '99.webm.part'
        self.assertEqual(partial.stat().st_size, 1024 * 1024)
        self.assertFalse((self.data / 'recordings' / '99.webm').exists())
        with self.assertRaises(pilot.PilotError):
            pilot.download()

    def test_prepare_is_idempotent_and_verifies_profile(self):
        content = b'{"synthetic_profile":true}\n'
        (self.data / 'seccomp-userns.json').write_bytes(content)
        with patch.object(pilot, 'PROFILE_SHA256', hashlib.sha256(content).hexdigest()):
            pilot.prepare()
            original = (self.data / '.env').read_bytes()
            pilot.prepare()
            self.assertEqual((self.data / '.env').read_bytes(), original)
        with self.assertRaisesRegex(pilot.PilotError, 'checksum mismatch'):
            pilot.prepare()

    def test_atomic_receipt_failure_retains_previous_state(self):
        target = self.data / 'receipt.json'
        target.write_text('original', encoding='utf-8')
        with patch.object(pilot.os, 'replace', side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):
                pilot.write_private(target, 'replacement', replace=True)
        self.assertEqual(target.read_text(), 'original')

    def test_check_refuses_remote_docker_capture_host(self):
        with patch.dict(pilot.os.environ, {'DOCKER_HOST': 'tcp://example.invalid:2375'}):
            with patch.object(pilot, 'run') as run:
                with self.assertRaisesRegex(pilot.PilotError, 'remote Docker endpoint'):
                    pilot.check()
                run.assert_not_called()
        with patch.dict(pilot.os.environ, {'DOCKER_HOST': ''}):
            with patch.object(pilot, 'run', return_value=json.dumps([{'Endpoints': {'docker': {'Host': 'ssh://example.invalid'}}}])):
                with self.assertRaisesRegex(pilot.PilotError, 'local Docker Desktop'):
                    pilot.check()


if __name__ == '__main__':
    unittest.main()

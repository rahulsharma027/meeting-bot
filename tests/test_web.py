import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lens.settings")
import django
django.setup()
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from lens import config, store


class WebTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.override = patch.object(config, "DATABASE", Path(self.folder.name)/"web.sqlite3")
        self.override.start()
        store.seed()
        self.client = Client(enforce_csrf_checks=True)
        self.client.get("/")
        self.headers = {"HTTP_X_CSRFTOKEN": self.client.cookies["csrftoken"].value}

    def tearDown(self):
        self.override.stop()
        self.folder.cleanup()

    def test_status_does_not_expose_secrets(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret-test-key"}):
            response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["documents"]), 6)
        self.assertNotIn("secret-test-key", response.content.decode())

    def test_csrf_enforced(self):
        response = self.client.post("/api/ask", data='{"question":"parser"}', content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_search_and_invalid_payload(self):
        response = self.client.post("/api/ask", data='{"question":"parser deadline"}', content_type="application/json", **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["sources"])
        for payload in ('[]', '{"question":5}', '{"question":"parser","top_k":true}', '{"question":"parser","generate":"yes"}'):
            response = self.client.post("/api/ask", data=payload, content_type="application/json", **self.headers)
            self.assertEqual(response.status_code, 400)

    def test_upload_and_duplicate(self):
        data = b"[00:00:01] User: A unique session about planning."
        for expected in (True, False):
            response = self.client.post("/api/upload", {"file": SimpleUploadedFile("session.txt", data)}, **self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["created"], expected)

    def test_audio_rejected(self):
        response = self.client.post("/api/upload", {"file": SimpleUploadedFile("recording.mp3", b"audio")}, **self.headers)
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__": unittest.main()

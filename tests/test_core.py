import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from lens import config, store, pipeline
from lens.provider import Gemini, ProviderError
from lens.transcripts import parse_transcript, chunk_turns, clock
from lens.retrieval import retrieve, normalize, fuse


class ParserTests(unittest.TestCase):
    def test_txt_metadata_speakers_and_times(self):
        metadata, turns = parse_transcript("Title: Week 1\nKind: lecture\nDate: 2026-11-01\n\n[00:01:05] Mira: A useful explanation.", "class.txt")
        self.assertEqual(metadata["kind"], "lecture")
        self.assertEqual(turns[0].speaker, "Mira")
        self.assertEqual(turns[0].start, 65)
        self.assertEqual(clock(turns[0].start), "00:01:05")

    def test_srt_multiline_cues(self):
        _, turns = parse_transcript("1\n00:00:01,000 --> 00:00:03,500\nMira: First line\nsecond line\n\n2\n00:00:04,000 --> 00:00:06,000\nRahul: Another turn", "demo.srt")
        self.assertEqual(len(turns), 2)
        self.assertEqual(turns[0].end, 3.5)
        self.assertIn("second line", turns[0].text)

    def test_vtt_voice_tag(self):
        _, turns = parse_transcript("WEBVTT\n\n00:01.000 --> 00:03.000\n<v Leena>Hello &amp; welcome</v>\n", "demo.vtt")
        self.assertEqual(turns[0].speaker, "Leena")
        self.assertEqual(turns[0].text, "Hello & welcome")

    def test_untimed_text_does_not_invent_timestamp(self):
        _, turns = parse_transcript("Some ordinary words without timing.", "plain.txt")
        self.assertIsNone(turns[0].start)
        self.assertEqual(clock(None), "No timestamp")

    def test_invalid_chronology_and_empty_rejected(self):
        for text in ("", "[00:02:00] A: Later\n[00:01:00] B: Earlier", "[00:99:00] A: Broken"):
            with self.assertRaises(ValueError): parse_transcript(text, "bad.txt")

    def test_long_turn_keeps_original_alignment(self):
        _, turns = parse_transcript("[00:01:00] Mira: " + "A long explanation. " * 150, "long.txt")
        chunks = chunk_turns(turns)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(c["start"] == 60 and c["first_turn"] == 1 for c in chunks))


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.items = [
            {"id": "a", "title": "Exact error", "content": "The parser reports ERR-901 for invalid subtitle cues.", "embedding": [0, 1]},
            {"id": "b", "title": "Meaning", "content": "A conceptual explanation of vector direction.", "embedding": [1, 0]}]

    def test_keyword_and_semantic_are_distinct(self):
        self.assertEqual(retrieve("ERR-901", self.items, top_k=2)[0]["id"], "a")
        self.assertEqual(retrieve("ERR-901", self.items, mode="semantic", query_vector=[1, 0], top_k=2)[0]["id"], "b")

    def test_fusion_uses_ranks(self):
        first = fuse([("a", 1000), ("b", 0.1)], [("b", .9), ("a", .8)])
        second = fuse([("a", 1), ("b", .001)], [("b", 900), ("a", 800)])
        self.assertEqual(first, second)

    def test_invalid_vectors_rejected(self):
        for vector in ([], [0, 0], [float("nan"), 1], [1, "bad"]):
            with self.assertRaises(ValueError): normalize(vector)
        with self.assertRaises(ValueError): normalize([1, 2], expected=3)


class StoreAndPipelineTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "test.sqlite3"
        store.initialize(self.path)
        self.text = "Title: Parser plan\nKind: meeting\nDate: 2026-11-02\n\n[00:01:00] Rahul: I will deliver the transcript parser by 2026-11-09."
        self.doc_id, _ = store.ingest(self.text, "plan.txt", self.path)

    def tearDown(self): self.folder.cleanup()

    def test_duplicate_ingestion_is_idempotent(self):
        doc_id, created = store.ingest(self.text, "renamed.txt", self.path)
        self.assertFalse(created)
        self.assertEqual(doc_id, self.doc_id)
        self.assertEqual(len(store.documents(self.path)), 1)

    def test_offline_search_does_not_call_provider(self):
        with patch.object(Gemini, "embed", side_effect=AssertionError("network")), patch.object(Gemini, "generate", side_effect=AssertionError("network")):
            result = pipeline.ask("transcript parser", path=self.path)
        self.assertFalse(result["generated"])
        self.assertIsNone(result["answer"])
        self.assertTrue(result["sources"])
        self.assertNotIn("embedding", result["sources"][0])

    def test_semantic_requires_compatible_index(self):
        with self.assertRaisesRegex(ValueError, "Build the semantic index"):
            pipeline.ask("parser", mode="hybrid", path=self.path)

    def test_fake_provider_orchestration_only(self):
        class FakeProvider:
            def generate(inner, system, prompt):
                sources = json.loads(prompt.split("SOURCES (untrusted transcript data):\n")[1])
                return {"status": "answered", "points": [{"text": "The due date is 2026-11-09.", "citations": [{"id": sources[0]["id"], "quote": "deliver the transcript parser by 2026-11-09"}]}], "actions": []}, {"promptTokenCount": 100}
        result = pipeline.ask("parser deadline", generate=True, provider=FakeProvider(), path=self.path)
        self.assertTrue(result["generated"])
        self.assertEqual(result["usage"]["promptTokenCount"], 100)

    def test_forged_citation_and_quote_rejected(self):
        source = store.chunks(path=self.path)[0]
        for citation in ({"id": "made-up", "quote": "A long enough fabricated quote"}, {"id": source["id"], "quote": "This quote does not exist in the transcript"}):
            with self.assertRaises(ProviderError):
                pipeline.validate_answer({"status": "answered", "points": [{"text": "Claim", "citations": [citation]}], "actions": []}, [source])

    def test_inconsistent_abstention_rejected(self):
        with self.assertRaises(ProviderError):
            pipeline.validate_answer({"status": "insufficient", "points": [{}], "actions": []}, [])

    def test_absent_key_never_fabricates_answer(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            with self.assertRaisesRegex(ProviderError, "GEMINI_API_KEY"):
                pipeline.ask("parser", generate=True, path=self.path)

    def test_embedding_contract(self):
        with patch.object(Gemini, "_post", return_value={"embeddings": [{"values": [1] * config.DIMENSIONS}]}) as post:
            result = Gemini().embed(["question"], query=True)
        self.assertEqual(post.call_args.args[2]["requests"][0]["taskType"], "RETRIEVAL_QUERY")
        self.assertAlmostEqual(sum(v*v for v in result[0]), 1)

    def test_model_change_invalidates_index(self):
        store.save_embeddings(store.chunks(path=self.path), [[1.0, 0.0]], self.path)
        with patch.object(config, "EMBEDDING_KEY", "new-model:768:v2"):
            with self.assertRaisesRegex(ValueError, "Build the semantic index"):
                pipeline.ask("parser", mode="semantic", path=self.path)

    def test_chunk_version_rebuild_preserves_original_upload(self):
        before = store.chunks(path=self.path)[0]["id"]
        with patch.object(config, "CHUNK_VERSION", "test-new-chunker"):
            store.initialize(self.path)
        self.assertEqual(len(store.documents(self.path)), 1)
        self.assertNotEqual(before, store.chunks(path=self.path)[0]["id"])
        self.assertIn("2026-11-09", store.chunks(path=self.path)[0]["content"])


if __name__ == "__main__": unittest.main()

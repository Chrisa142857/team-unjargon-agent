import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("bridge", Path(__file__).parents[1] / "team_unjargon_bridge.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class BridgeTests(unittest.TestCase):
    def test_candidate_detector_discards_plain_lowercase_prose(self):
        self.assertEqual(bridge.candidates("please update the file and run tests"), [])

    def test_candidate_detector_emits_terms_not_text(self):
        self.assertEqual(bridge.candidates("Use RAG with a vector database and track SLO."), ["RAG", "SLO", "vector database"])

    def test_claude_parser_only_reads_assistant_text(self):
        row = {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "Use RAG."}]}}
        self.assertEqual(bridge.assistant_text("claude", row), "Use RAG.")

    def test_scan_caps_events_across_files(self):
        row = json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "Use RAG."}]}})
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / "first.jsonl", root / "second.jsonl"
            first.write_text(row + "\n")
            second.write_text(row + "\n")
            offsets = {str(first): 0, str(second): 0}
            with patch.object(bridge, "post") as post:
                remaining = bridge.scan(root, "claude", offsets, "https://example.test", 1)
            self.assertEqual(remaining, 0)
            self.assertEqual(post.call_count, 1)

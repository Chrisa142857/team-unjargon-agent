import importlib.util
import unittest
from pathlib import Path

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

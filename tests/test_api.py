import os
import unittest

os.environ["TEAM_UNJARGON_DEMO_MODE"] = "true"
os.environ["USE_FIRESTORE"] = "false"

from fastapi.testclient import TestClient
from app.main import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_blank_term_is_rejected(self):
        response = self.client.post("/api/explain", json={"member": "Member A", "term": ""})
        self.assertEqual(response.status_code, 422)
        self.assertIn("Term is required", response.json()["detail"])

    def test_correction_is_shared_without_request_context(self):
        saved = self.client.post(
            "/api/feedback",
            json={"member": "Member A", "term": "Runbook", "correction": "A short operational recovery guide."},
        )
        self.assertEqual(saved.status_code, 200)
        self.assertNotIn("context", saved.json()["record"])
        answer = self.client.post(
            "/api/explain",
            json={"member": "Member B", "term": "Runbook"},
        )
        self.assertEqual(answer.status_code, 200)
        self.assertEqual(answer.json()["definition"], "A short operational recovery guide.")
        self.assertEqual(answer.json()["source"], "team memory")

    def test_explain_rejects_raw_context(self):
        response = self.client.post(
            "/api/explain",
            json={"member": "Member A", "term": "ADR", "context": "private transcript text"},
        )
        self.assertEqual(response.status_code, 422)

    def test_detection_event_creates_review_only_for_unknown_terms(self):
        response = self.client.post(
            "/api/detection-events",
            json={"source": "Codex", "candidates": ["ADR", "RAG", "RAG"]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["received"], 2)
        self.assertEqual(response.json()["aligned"], 1)
        self.assertEqual(response.json()["needs_review"], 1)
        run = self.client.get("/api/agent-run").json()["run"]
        self.assertEqual(run["aligned"], 1)
        self.assertEqual(run["needs_review"], 1)
        self.assertEqual(run["decisions"][0]["action"], "Aligned")
        self.assertNotIn("transcript", str(run))
        self.assertEqual(self.client.get("/api/agent-run").headers["cache-control"], "no-store")
        inbox = self.client.get("/api/inbox").json()["tasks"]
        adr = next(task for task in inbox if task["term"] == "ADR")
        self.assertIn("Architecture Decision Record", adr["team_definition"])
        rag = next(task for task in inbox if task["term"] == "RAG")
        self.assertEqual(rag["status"], "needs_review")
        self.assertNotIn("context", rag)

    def test_glossary_markdown_exports_and_imports_definitions_only(self):
        exported = self.client.get("/api/glossary.md")
        self.assertEqual(exported.status_code, 200)
        self.assertIn("## ADR", exported.text)
        shared = self.client.post(
            "/api/glossary-import",
            json={
                "member": "Member B",
                "markdown": "# unjargon glossary\n\n## RAG\n\nRetrieval-Augmented Generation combines retrieved knowledge with a model response.\n\nprivate transcript text is ignored\n",
            },
        )
        self.assertEqual(shared.status_code, 200)
        self.assertEqual(shared.json()["imported"], 1)
        answer = self.client.post("/api/explain", json={"member": "Member A", "term": "RAG"})
        self.assertEqual(answer.json()["definition"], "Retrieval-Augmented Generation combines retrieved knowledge with a model response.")


if __name__ == "__main__":
    unittest.main()

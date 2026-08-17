# Team unjargon agent

A Gemini Collaborative Partner that automatically maintains an AI-native team's shared vocabulary. It receives detected term candidates from a privacy-preserving connector, aligns known terms, and asks the team to review only unresolved meanings.

**Live demo:** https://team-unjargon-agent-gwygowb26q-uc.a.run.app

## Local demo

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
TEAM_UNJARGON_DEMO_MODE=true uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` and choose **Run demo incoming feed**. The agent receives candidate terms only, automatically aligns `ADR` when known, and creates review tasks for unknown terms. Open a review task, generate a Gemini draft, then approve it; later detections will align automatically. Run the regression checks with:

```bash
python -m unittest discover -s tests -v
```

The deployed health endpoint is `/api/healthz`.

## Automatic local bridge

The new bridge is independent from the original unjargon.app collector. It reads Claude Code and Codex assistant output locally, extracts conservative jargon candidates, and uploads only `{source, candidates}` — never message text, paths, session IDs, or user prompts.

```bash
python3 team_unjargon_bridge.py --server https://team-unjargon-agent-gwygowb26q-uc.a.run.app --watch
```

It records local byte offsets in `~/.local/state/team-unjargon-bridge/offsets.json`, so later runs send only new assistant output. Its first scan starts at the current end of existing history, preventing an accidental archive upload, and each scan caps itself at 20 candidate events before resuming next time. It is intentionally a candidate detector rather than an explainer; Team unjargon performs the shared-memory triage and review workflow.

## Google Cloud production mode

1. Create a Google Cloud project, enable Cloud Run, Firestore, Vertex AI, and Artifact Registry APIs, and create a Firestore Native database.
2. Authenticate `gcloud`, choose the project, and deploy:

```bash
gcloud run deploy team-unjargon-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars USE_FIRESTORE=true,TEAM_UNJARGON_DEMO_MODE=false,GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,GEMINI_MODEL=gemini-2.5-flash
```

3. Grant the Cloud Run runtime service account the least-privilege Firestore access and the Vertex AI User role. Then seed one term through the UI and show the two-member retrieval flow.

The live path uses Google ADK (`LlmAgent`, `Runner`, and `InMemorySessionService`) to call Gemini. The only persistent records are team terms, candidate-derived task state, and explicit feedback — never an agent message or short context. Set `GEMINI_MODEL` to Gemini 3.5 Flash when that model is enabled for the project; the deployed compatibility baseline is Gemini 2.5 Flash.

See [ARCHITECTURE.md](ARCHITECTURE.md), [PRE_EXISTING_WORK.md](PRE_EXISTING_WORK.md), and [DEMO.md](DEMO.md).

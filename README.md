# Team unjargon agent

A Gemini Collaborative Partner for AI-native teams. It turns one confusing term into a concise explanation, learns from explicit team corrections, and never collects an agent transcript.

## Local demo

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
TEAM_UNJARGON_DEMO_MODE=true uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`. Ask about `ADR`, save a correction as Member A, switch to Member B, and ask again. Run the regression checks with:

```bash
python -m unittest discover -s tests -v
```

## Google Cloud production mode

1. Create a Google Cloud project, enable Cloud Run, Firestore, Vertex AI, and Artifact Registry APIs, and create a Firestore Native database.
2. Authenticate `gcloud`, choose the project, and deploy:

```bash
gcloud run deploy team-unjargon-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars USE_FIRESTORE=true,TEAM_UNJARGON_DEMO_MODE=false,GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,GEMINI_MODEL=gemini-3.5-flash
```

3. Grant the Cloud Run runtime service account the least-privilege Firestore access and the Vertex AI User role. Then seed one term through the UI and show the two-member retrieval flow.

The live path uses Google ADK (`LlmAgent`, `Runner`, and `InMemorySessionService`) to call Gemini. The only persistent records are team terms and explicit feedback.

See [ARCHITECTURE.md](ARCHITECTURE.md) and [PRE_EXISTING_WORK.md](PRE_EXISTING_WORK.md).

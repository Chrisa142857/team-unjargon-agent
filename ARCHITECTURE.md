# Architecture

```text
Local detector / connector
  | high-confidence candidate terms + source category only
  v
FastAPI on Cloud Run
  |-- autonomous triage: align known terms or create review work
  |-- Google ADK + Gemini: draft a review explanation on demand
  `-- Firestore: team terms + candidate-derived task state + explicit feedback
```

The detector calls `POST /api/detection-events` with only candidate terms and a source category. The service automatically checks `teams/demo-team/terms/{normalized-term}` and stores a task as either `aligned` or `needs_review`; it does not accept a raw agent message. A reviewer may open a task through `POST /api/explain`, which accepts only a term and member name, where Google ADK + Gemini drafts a definition. `POST /api/feedback` persists an explicit approval; future detector events then align that term automatically.

For local product walkthroughs, `TEAM_UNJARGON_DEMO_MODE=true` uses deterministic responses and in-memory storage. Cloud Run sets it to `false` and `USE_FIRESTORE=true` so the same flow uses Gemini through ADK and Firestore.

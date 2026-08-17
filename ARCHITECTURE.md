# Architecture

```text
Browser
  | term + optional short context (request-only)
  v
FastAPI on Cloud Run
  |-- Google ADK + Gemini: contextual explanation
  `-- Firestore: team terms + explicit feedback only
```

The browser calls `POST /api/explain`. The service retrieves only the requested term from `teams/demo-team/terms/{normalized-term}`. Gemini receives the term, optional short context, and that term-level memory. `POST /api/feedback` persists a useful signal or an explicit correction; it does not accept or store a transcript field.

For local product walkthroughs, `TEAM_UNJARGON_DEMO_MODE=true` uses deterministic responses and in-memory storage. Cloud Run sets it to `false` and `USE_FIRESTORE=true` so the same flow uses Gemini through ADK and Firestore.

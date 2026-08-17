# Three-minute demo script

## 0:00–0:20 — problem and privacy

Open the Cloud Run URL. Explain that agent vocabulary travels faster than a team’s shared understanding. Point to the privacy statement: this project does not collect or display agent transcripts.

## 0:20–1:05 — live Gemini Collaborative Partner

Enter a confusing term and one optional sentence of context. Show the response’s source label, plain-language definition, why it matters, next action, and any clarification. Explain that the request runs through Google ADK to Gemini.

## 1:05–1:55 — shared learning loop

As Member A, enter a concise corrected explanation and save it. Switch the selector to Member B, clear the optional context, and request the same term. Show that the source now says `team memory + Gemini + ADK` and that the new definition appears.

## 1:55–2:30 — Google Cloud proof

Open `/api/healthz` to show the deployed Cloud Run service reports `memory: firestore`. In Google Cloud Console, show the Cloud Run service, the Firestore Native database, and the saved `teams/demo-team/terms` record. Its fields are a term, an explicit correction, helpful count, and timestamp — not a transcript.

## Closing

Show `ARCHITECTURE.md` and `PRE_EXISTING_WORK.md`. State that Team unjargon agent is new hackathon work and that the older open-source unjargon.app inspired the problem but its code and data are not included.

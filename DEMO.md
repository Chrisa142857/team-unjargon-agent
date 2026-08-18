# Three-minute demo script

## 0:00–0:20 — problem and privacy

Open the Cloud Run URL. Explain that people meet unknown jargon while working with AI agents, then choose what they have learned to share with a team. Point to the privacy statement: the connector emits candidate terms and a source category, not agent transcripts.

## 0:20–1:10 — autonomous learning run

Click **Run demo incoming feed**. Show that the agent receives a batch of candidate terms, deduplicates repeats, finds a previously shared explanation, and leaves only unknown terms to learn. This is the event-driven work the agent completes before asking a person for help.

## 1:10–2:05 — shared learning loop

Open one new-jargon task. Ask Gemini to draft a concise explanation, improve it as Member A, and add it to the team glossary. Download the Markdown glossary, then paste it into **Import a teammate’s shared Markdown** as Member B. Explain that future detections show the chosen explanation without exposing the originating output.

## 1:55–2:30 — Google Cloud proof

Open `/api/healthz` to show the deployed Cloud Run service reports `memory: firestore`. Trigger one concise term explanation and show its `Gemini + ADK` source, then show the Cloud Run service, the Firestore Native database, and the saved `teams/demo-team/terms` record. Its fields are a term, an explicit correction, helpful count, and timestamp — not a transcript.

## Closing

Show `ARCHITECTURE.md` and `PRE_EXISTING_WORK.md`. State that Team unjargon agent is new hackathon work and that the older open-source unjargon.app inspired the problem but its code and data are not included.

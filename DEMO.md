# Four-minute demo script

## 0:00–0:30 — problem and privacy

Open the Cloud Run URL. Explain that people meet unknown jargon while working with AI agents, then choose what they have learned to share with a team. Point to the privacy statement: the connector emits candidate terms and a source category, not agent transcripts.

## 0:30–1:25 — autonomous learning run

Click **Run demo incoming feed**. Show that the agent receives a batch of candidate terms, deduplicates repeats, finds a previously shared explanation, and leaves only unknown terms to learn. Point to the **Autonomous decision log**: it visibly records each term-level routing action while storing no transcript. This is the event-driven work the agent completes before asking a person for help.

## 1:25–2:25 — Gemini-assisted learning

Open one new-jargon task. Ask Gemini to draft a concise explanation, improve it as Member A, and add it to the team glossary. State that Gemini receives only the term plus deliberately shared team knowledge, never the original AI conversation.

## 2:25–3:10 — feedback changes the next run

Run the same incoming feed again. Show that the reviewed term now moves from **Queued** to **Aligned** in the decision log without a second Gemini call. Download the Markdown glossary, then paste it into **Import a teammate’s shared Markdown** as Member B. Explain that future detections show the chosen explanation without exposing the originating output.

## 3:10–4:00 — Google Cloud proof and close

Open `/api/healthz` to show the deployed Cloud Run service reports `memory: firestore`. Trigger one concise term explanation and show its `Gemini + ADK` source, then show the Cloud Run service, Vertex AI request evidence, and the Firestore `teams/demo-team` records. Their fields are terms, explicit feedback, task state, and routing decisions — not a transcript. Close on `ARCHITECTURE.md` and `PRE_EXISTING_WORK.md`, stating that Team unjargon agent is new hackathon work and the older open-source unjargon.app inspired the problem but its code and data are not included.

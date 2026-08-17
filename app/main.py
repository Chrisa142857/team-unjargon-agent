from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .agent import TeamUnjargonPartner
from .memory import FirestoreTeamMemory, InMemoryTeamMemory

TEAM_ID = "demo-team"
static_dir = Path(__file__).resolve().parents[1] / "static"


def create_memory():
    if os.getenv("USE_FIRESTORE", "false").lower() == "true":
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
        if not project_id:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is required when USE_FIRESTORE=true.")
        return FirestoreTeamMemory(project_id)
    memory = InMemoryTeamMemory()
    memory.seed(
        TEAM_ID,
        "ADR",
        "An Architecture Decision Record is a short, durable note explaining one important technical choice.",
        "Our team uses ADRs to prevent an AI agent or new teammate from reopening an already-settled decision.",
    )
    return memory


memory = create_memory()
partner = TeamUnjargonPartner(memory)
app = FastAPI(title="Team unjargon agent")


class ExplainRequest(BaseModel):
    member: str
    term: str
    context: str = ""


class FeedbackRequest(BaseModel):
    member: str
    term: str
    useful: bool | None = None
    correction: str = ""


def clean(value: str, name: str, limit: int) -> str:
    result = value.strip()
    if not result:
        raise HTTPException(422, f"{name} is required.")
    if len(result) > limit:
        raise HTTPException(422, f"{name} must be {limit} characters or fewer.")
    return result


@app.get("/")
def index():
    return FileResponse(static_dir / "index.html")


@app.get("/app.js")
def javascript():
    return FileResponse(static_dir / "app.js", media_type="text/javascript")


@app.get("/styles.css")
def styles():
    return FileResponse(static_dir / "styles.css", media_type="text/css")


def health_payload():
    return {"ok": True, "memory": "firestore" if isinstance(memory, FirestoreTeamMemory) else "in-memory"}


@app.get("/healthz")
@app.get("/api/healthz")
def healthz():
    return health_payload()


@app.post("/api/explain")
async def explain(request: ExplainRequest):
    term = clean(request.term, "Term", 80)
    member = clean(request.member, "Member", 40)
    context = request.context.strip()
    if len(context) > 500:
        raise HTTPException(422, "Optional context must be 500 characters or fewer.")
    try:
        return vars(await partner.explain(TEAM_ID, member, term, context))
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error


@app.post("/api/feedback")
def feedback(request: FeedbackRequest):
    term = clean(request.term, "Term", 80)
    member = clean(request.member, "Member", 40)
    correction = request.correction.strip()
    if correction:
        record = memory.save_correction(TEAM_ID, term, clean(correction, "Correction", 400), member)
        return {"status": "saved", "record": vars(record)}
    if request.useful is True:
        record = memory.mark_useful(TEAM_ID, term, member)
        if not record:
            raise HTTPException(404, "Save a correction before marking this new term useful.")
        return {"status": "counted", "record": vars(record)}
    return {"status": "noted"}

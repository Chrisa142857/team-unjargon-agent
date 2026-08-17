from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict

from .agent import TeamUnjargonPartner
from .memory import FirestoreTeamMemory, InMemoryTeamMemory

TEAM_ID = "demo-team"
static_dir = Path(__file__).resolve().parents[1] / "static"


def create_memory():
    if os.getenv("USE_FIRESTORE", "false").lower() == "true":
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
        if not project_id:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is required when USE_FIRESTORE=true.")
        repo = FirestoreTeamMemory(project_id)
    else:
        repo = InMemoryTeamMemory()
    repo.seed(
        TEAM_ID,
        "ADR",
        "An Architecture Decision Record is a short, durable note explaining one important technical choice.",
        "Our team uses ADRs to prevent an AI agent or new teammate from reopening an already-settled decision.",
    )
    return repo


memory = create_memory()
partner = TeamUnjargonPartner(memory)
app = FastAPI(title="Team unjargon agent")


class ExplainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    member: str
    term: str


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    member: str
    term: str
    useful: bool | None = None
    correction: str = ""


class DetectionEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    candidates: list[str]


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
    try:
        return vars(await partner.explain(TEAM_ID, member, term))
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error


@app.get("/api/inbox")
def inbox():
    tasks = []
    for task in memory.list_tasks(TEAM_ID):
        item = vars(task)
        record = memory.get_term(TEAM_ID, task.term)
        item["team_definition"] = record.definition if record else None
        tasks.append(item)
    return {"tasks": tasks}


@app.post("/api/detection-events")
def detection_events(request: DetectionEventRequest):
    source = clean(request.source, "Source", 40)
    candidates = []
    for candidate in request.candidates[:12]:
        term = candidate.strip()
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9 -]{0,78}", term) and term not in candidates:
            candidates.append(term)
    if not candidates:
        raise HTTPException(422, "At least one detected term is required.")
    # The event carries candidates only. Raw agent output is never accepted or persisted here.
    tasks = memory.observe_terms(TEAM_ID, candidates, source)
    return {
        "received": len(candidates),
        "aligned": sum(task.status == "aligned" for task in tasks),
        "needs_review": sum(task.status == "needs_review" for task in tasks),
        "tasks": [vars(task) for task in tasks],
    }


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

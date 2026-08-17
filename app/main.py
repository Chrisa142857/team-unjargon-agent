from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
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


def observe_candidate_terms(source: str, candidates: list[str]) -> dict:
    source = clean(source, "Source", 40)
    accepted = []
    for candidate in candidates[:12]:
        term = candidate.strip()
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9 -]{0,78}", term) and term not in accepted:
            accepted.append(term)
    if not accepted:
        raise HTTPException(422, "At least one detected term is required.")
    tasks = memory.observe_terms(TEAM_ID, accepted, source)
    return {
        "received": len(accepted),
        "aligned": sum(task.status == "aligned" for task in tasks),
        "needs_review": sum(task.status == "needs_review" for task in tasks),
        "tasks": [vars(task) for task in tasks],
    }


def create_mcp() -> MCPServer:
    mcp = MCPServer(
        "Team unjargon agent",
        instructions="Use these tools to retrieve or update the team glossary. Submit only jargon candidates, never raw agent messages, prompts, paths, or session IDs.",
    )

    @mcp.tool()
    def lookup_team_term(term: str) -> dict:
        """Look up the team-approved meaning of one term without sending conversation context."""
        term = clean(term, "Term", 80)
        record = memory.get_term(TEAM_ID, term)
        if not record:
            return {"found": False, "term": term}
        return {"found": True, "term": record.term, "definition": record.definition, "helpful_count": record.helpful_count}

    @mcp.tool()
    def list_learning_inbox() -> list[dict]:
        """List glossary terms awaiting review or already aligned for the team."""
        result = []
        for task in memory.list_tasks(TEAM_ID):
            record = memory.get_term(TEAM_ID, task.term)
            result.append({**vars(task), "team_definition": record.definition if record else None})
        return result

    @mcp.tool()
    def submit_detected_terms(source: str, candidates: list[str]) -> dict:
        """Submit up to 12 detected jargon candidates. Never submit source text or transcript context."""
        return observe_candidate_terms(source, candidates)

    @mcp.tool()
    def save_team_definition(member: str, term: str, definition: str) -> dict:
        """Save a team-approved, concise definition after a teammate has reviewed a term."""
        member = clean(member, "Member", 40)
        term = clean(term, "Term", 80)
        record = memory.save_correction(TEAM_ID, term, clean(definition, "Definition", 400), member)
        return {"status": "saved", "term": record.term, "definition": record.definition}

    return mcp


mcp = create_mcp()
default_mcp_hosts = [
    "team-unjargon-agent-gwygowb26q-uc.a.run.app",
    "team-unjargon-agent-170101312348.us-central1.run.app",
    "localhost:*",
    "127.0.0.1:*",
    "testserver",
]
mcp_hosts = os.getenv("MCP_ALLOWED_HOSTS", ",".join(default_mcp_hosts)).split(",")
mcp_security = TransportSecuritySettings(allowed_hosts=[host.strip() for host in mcp_hosts if host.strip()])


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Team unjargon agent", lifespan=lifespan)


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
    # The event carries candidates only. Raw agent output is never accepted or persisted here.
    return observe_candidate_terms(request.source, request.candidates)


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


# Mount last so the MCP endpoint is exactly /mcp (without a redirect to /mcp/).
app.mount("", mcp.streamable_http_app(streamable_http_path="/mcp", json_response=True, stateless_http=True, transport_security=mcp_security))

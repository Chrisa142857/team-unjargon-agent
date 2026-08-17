"""Team term memory and its autonomous review queue. Raw agent text never enters here."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Literal, Protocol


def normalize(term: str) -> str:
    return " ".join(term.lower().split())


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class TermRecord:
    term: str
    definition: str
    team_context: str
    helpful_count: int = 0
    updated_at: str = ""


@dataclass(frozen=True)
class LearningTask:
    term: str
    status: Literal["aligned", "needs_review"]
    sightings: int
    source: str
    reason: str
    updated_at: str


class TeamMemory(Protocol):
    def get_term(self, team_id: str, term: str) -> TermRecord | None: ...
    def list_terms(self, team_id: str) -> list[TermRecord]: ...
    def save_correction(self, team_id: str, term: str, definition: str, member: str) -> TermRecord: ...
    def mark_useful(self, team_id: str, term: str, member: str) -> TermRecord | None: ...
    def observe_terms(self, team_id: str, terms: list[str], source: str) -> list[LearningTask]: ...
    def list_tasks(self, team_id: str) -> list[LearningTask]: ...


class InMemoryTeamMemory:
    """Development repository; all write methods intentionally accept terms, never context."""

    def __init__(self) -> None:
        self._terms: dict[tuple[str, str], TermRecord] = {}
        self._tasks: dict[tuple[str, str], LearningTask] = {}

    def seed(self, team_id: str, term: str, definition: str, team_context: str) -> None:
        key = (team_id, normalize(term))
        self._terms.setdefault(key, TermRecord(term, definition, team_context, updated_at=now()))

    def get_term(self, team_id: str, term: str) -> TermRecord | None:
        record = self._terms.get((team_id, normalize(term)))
        return replace(record) if record else None

    def list_terms(self, team_id: str) -> list[TermRecord]:
        return sorted((replace(record) for (team, _), record in self._terms.items() if team == team_id), key=lambda record: record.term.lower())

    def save_correction(self, team_id: str, term: str, definition: str, member: str) -> TermRecord:
        existing = self.get_term(team_id, term)
        record = TermRecord(term.strip(), definition.strip(), existing.team_context if existing else "Team-approved learning", existing.helpful_count if existing else 0, now())
        self._terms[(team_id, normalize(term))] = record
        self._tasks[(team_id, normalize(term))] = LearningTask(record.term, "aligned", self._tasks.get((team_id, normalize(term)), LearningTask(record.term, "aligned", 0, "team", "", now())).sightings, "team", "A teammate shared this explanation.", now())
        return replace(record)

    def mark_useful(self, team_id: str, term: str, member: str) -> TermRecord | None:
        existing = self.get_term(team_id, term)
        if not existing:
            return None
        record = replace(existing, helpful_count=existing.helpful_count + 1, updated_at=now())
        self._terms[(team_id, normalize(term))] = record
        return replace(record)

    def observe_terms(self, team_id: str, terms: list[str], source: str) -> list[LearningTask]:
        tasks = []
        for term in dict.fromkeys(terms):
            key = (team_id, normalize(term))
            old = self._tasks.get(key)
            known = self.get_term(team_id, term)
            task = LearningTask(
                term=term,
                status="aligned" if known else "needs_review",
                sightings=(old.sightings if old else 0) + 1,
                source=source,
                reason="A teammate has already shared a concise explanation." if known else "New jargon detected; no shared explanation yet.",
                updated_at=now(),
            )
            self._tasks[key] = task
            tasks.append(replace(task))
        return tasks

    def list_tasks(self, team_id: str) -> list[LearningTask]:
        return sorted((replace(task) for (team, _), task in self._tasks.items() if team == team_id), key=lambda task: (task.status == "aligned", -task.sightings, task.term.lower()))


class FirestoreTeamMemory:
    """Production memory: terms and event-derived task state, never messages or context."""

    def __init__(self, project_id: str) -> None:
        from google.cloud import firestore
        self.client = firestore.Client(project=project_id)

    def _terms(self, team_id: str):
        return self.client.collection("teams").document(team_id).collection("terms")

    def _tasks(self, team_id: str):
        return self.client.collection("teams").document(team_id).collection("tasks")

    def seed(self, team_id: str, term: str, definition: str, team_context: str) -> None:
        ref = self._terms(team_id).document(normalize(term))
        if not ref.get().exists:
            ref.set(asdict(TermRecord(term, definition, team_context, updated_at=now())))

    def get_term(self, team_id: str, term: str) -> TermRecord | None:
        snapshot = self._terms(team_id).document(normalize(term)).get()
        return TermRecord(**snapshot.to_dict()) if snapshot.exists else None

    def list_terms(self, team_id: str) -> list[TermRecord]:
        return sorted((TermRecord(**doc.to_dict()) for doc in self._terms(team_id).stream()), key=lambda record: record.term.lower())

    def save_correction(self, team_id: str, term: str, definition: str, member: str) -> TermRecord:
        existing = self.get_term(team_id, term)
        record = TermRecord(term.strip(), definition.strip(), existing.team_context if existing else "Team-approved learning", existing.helpful_count if existing else 0, now())
        self._terms(team_id).document(normalize(term)).set(asdict(record))
        old = self._tasks(team_id).document(normalize(term)).get()
        sightings = old.to_dict().get("sightings", 0) if old.exists else 0
        task = LearningTask(record.term, "aligned", sightings, "team", "A teammate shared this explanation.", now())
        self._tasks(team_id).document(normalize(term)).set(asdict(task))
        self.client.collection("teams").document(team_id).collection("feedback").add({"member": member, "term": record.term, "correction": record.definition, "created_at": now()})
        return record

    def mark_useful(self, team_id: str, term: str, member: str) -> TermRecord | None:
        record = self.get_term(team_id, term)
        if not record:
            return None
        updated = replace(record, helpful_count=record.helpful_count + 1, updated_at=now())
        self._terms(team_id).document(normalize(term)).set(asdict(updated))
        self.client.collection("teams").document(team_id).collection("feedback").add({"member": member, "term": updated.term, "useful": True, "created_at": now()})
        return updated

    def observe_terms(self, team_id: str, terms: list[str], source: str) -> list[LearningTask]:
        tasks = []
        for term in dict.fromkeys(terms):
            ref = self._tasks(team_id).document(normalize(term))
            old = ref.get()
            old_data = old.to_dict() if old.exists else {}
            known = self.get_term(team_id, term)
            task = LearningTask(term, "aligned" if known else "needs_review", int(old_data.get("sightings", 0)) + 1, source, "A teammate has already shared a concise explanation." if known else "New jargon detected; no shared explanation yet.", now())
            ref.set(asdict(task))
            tasks.append(task)
        return tasks

    def list_tasks(self, team_id: str) -> list[LearningTask]:
        tasks = [LearningTask(**doc.to_dict()) for doc in self._tasks(team_id).stream()]
        return sorted(tasks, key=lambda task: (task.status == "aligned", -task.sightings, task.term.lower()))

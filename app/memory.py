"""Term-level team memory. Request context never enters this module."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Protocol


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


class TeamMemory(Protocol):
    def get_term(self, team_id: str, term: str) -> TermRecord | None: ...

    def save_correction(self, team_id: str, term: str, definition: str, member: str) -> TermRecord: ...

    def mark_useful(self, team_id: str, term: str, member: str) -> TermRecord | None: ...


class InMemoryTeamMemory:
    """Development repository; its narrow methods make transcript persistence impossible."""

    def __init__(self) -> None:
        self._terms: dict[tuple[str, str], TermRecord] = {}

    def seed(self, team_id: str, term: str, definition: str, team_context: str) -> None:
        key = (team_id, normalize(term))
        self._terms.setdefault(key, TermRecord(term, definition, team_context, updated_at=now()))

    def get_term(self, team_id: str, term: str) -> TermRecord | None:
        record = self._terms.get((team_id, normalize(term)))
        return replace(record) if record else None

    def save_correction(self, team_id: str, term: str, definition: str, member: str) -> TermRecord:
        existing = self.get_term(team_id, term)
        record = TermRecord(
            term=term.strip(),
            definition=definition.strip(),
            team_context=existing.team_context if existing else "Team-approved learning",
            helpful_count=existing.helpful_count if existing else 0,
            updated_at=now(),
        )
        self._terms[(team_id, normalize(term))] = record
        return replace(record)

    def mark_useful(self, team_id: str, term: str, member: str) -> TermRecord | None:
        existing = self.get_term(team_id, term)
        if not existing:
            return None
        record = replace(existing, helpful_count=existing.helpful_count + 1, updated_at=now())
        self._terms[(team_id, normalize(term))] = record
        return replace(record)


class FirestoreTeamMemory:
    """Firestore implementation used in Cloud Run. It persists terms and explicit feedback only."""

    def __init__(self, project_id: str) -> None:
        from google.cloud import firestore

        self.client = firestore.Client(project=project_id)

    def _doc(self, team_id: str, term: str):
        return self.client.collection("teams").document(team_id).collection("terms").document(normalize(term))

    def get_term(self, team_id: str, term: str) -> TermRecord | None:
        snapshot = self._doc(team_id, term).get()
        if not snapshot.exists:
            return None
        data = snapshot.to_dict()
        return TermRecord(**data)

    def save_correction(self, team_id: str, term: str, definition: str, member: str) -> TermRecord:
        existing = self.get_term(team_id, term)
        record = TermRecord(
            term=term.strip(),
            definition=definition.strip(),
            team_context=existing.team_context if existing else "Team-approved learning",
            helpful_count=existing.helpful_count if existing else 0,
            updated_at=now(),
        )
        self._doc(team_id, term).set(asdict(record))
        self.client.collection("teams").document(team_id).collection("feedback").add(
            {"member": member, "term": record.term, "useful": None, "correction": record.definition, "created_at": now()}
        )
        return record

    def mark_useful(self, team_id: str, term: str, member: str) -> TermRecord | None:
        record = self.get_term(team_id, term)
        if not record:
            return None
        updated = replace(record, helpful_count=record.helpful_count + 1, updated_at=now())
        self._doc(team_id, term).set(asdict(updated))
        self.client.collection("teams").document(team_id).collection("feedback").add(
            {"member": member, "term": updated.term, "useful": True, "created_at": now()}
        )
        return updated

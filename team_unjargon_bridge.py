#!/usr/bin/env python3
"""Privacy-preserving local bridge for Claude Code and Codex transcript files.

It reads assistant text locally, extracts conservative candidate terms, and sends
only `{source, candidates}` to Team unjargon. It never sends a message, path,
session id, or user text.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

ACRONYM = re.compile(r"\b[A-Z]{3,}[0-9]*\b")
CONTEXTUAL = ("runbook", "vector database", "embedding", "retrieval", "latency", "migration")
MAX_EVENTS_PER_SCAN = 20


def candidates(text: str) -> list[str]:
    """Conservative local detector; intentional ceiling: it emits candidates, not definitions."""
    found = ACRONYM.findall(text)
    lower = text.lower()
    if found:
        found.extend(term for term in CONTEXTUAL if term in lower)
    return list(dict.fromkeys(found))[:6]


def assistant_text(tool: str, row: dict) -> str:
    if tool == "claude":
        message = row.get("message", {})
        if row.get("type") != "assistant" or message.get("role") != "assistant":
            return ""
        content = message.get("content", [])
        if isinstance(content, str):
            return content
        return "\n".join(block.get("text", "") for block in content if isinstance(block, dict) and block.get("type") == "text")
    if row.get("type") != "response_item":
        return ""
    item = row.get("payload", {})
    if item.get("type") != "message" or item.get("role") != "assistant":
        return ""
    return "\n".join(block.get("text", "") for block in item.get("content", []) if isinstance(block, dict) and block.get("type") in {"output_text", "text"})


def post(server: str, source: str, terms: list[str]) -> None:
    body = json.dumps({"source": source, "candidates": terms}).encode()
    request = urllib.request.Request(f"{server.rstrip('/')}/api/detection-events", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=15) as response:
        response.read()


def scan(root: Path, tool: str, offsets: dict[str, int], server: str) -> None:
    for path in root.rglob("*.jsonl"):
        key = str(path)
        if key not in offsets:
            # ponytail: live-only by default; add an explicit capped backfill command if history import is needed.
            offsets[key] = path.stat().st_size
            continue
        start = offsets.get(key, 0)
        try:
            with path.open("rb") as handle:
                handle.seek(start)
                sent = 0
                while line := handle.readline():
                    try:
                        terms = candidates(assistant_text(tool, json.loads(line)))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    if terms:
                        post(server, "Claude Code" if tool == "claude" else "Codex", terms)
                        sent += 1
                        if sent >= MAX_EVENTS_PER_SCAN:
                            break
                offsets[key] = handle.tell()
        except OSError:
            continue


def main() -> None:
    parser = argparse.ArgumentParser(description="Send local jargon candidates to Team unjargon without sending transcripts.")
    parser.add_argument("--server", required=True)
    parser.add_argument("--watch", action="store_true", help="Keep scanning every 30 seconds.")
    parser.add_argument("--state", type=Path, default=Path.home() / ".local/state/team-unjargon-bridge/offsets.json")
    args = parser.parse_args()
    roots = [(Path.home() / ".claude/projects", "claude"), (Path.home() / ".codex/sessions", "codex")]
    args.state.parent.mkdir(parents=True, exist_ok=True)
    offsets = json.loads(args.state.read_text()) if args.state.exists() else {}
    while True:
        for root, tool in roots:
            if root.exists():
                scan(root, tool, offsets, args.server)
        args.state.write_text(json.dumps(offsets))
        if not args.watch:
            return
        time.sleep(30)


if __name__ == "__main__":
    main()

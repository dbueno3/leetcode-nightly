"""Core engine for the NeetCode 150 nightly practice tool.

Single source of truth = state.json in the repo.
"Tonight's problem" is deterministic: the lowest-id problem not yet completed.
Because we always pick the lowest undone id and `done` only grows, you march
through all 150 in topic order with zero repeats -- no scheduling state needed.
"""
from __future__ import annotations

import json
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "neetcode150.json"
STATE_FILE = ROOT / "state.json"

DEFAULT_STATE = {
    "done": [],          # problem ids fully completed (main pass)
    "flagged": [],       # ids marked hard -> resurfaced in review pass
    "review_done": [],   # flagged ids re-completed in review pass
    "notes": {},         # {"<id>": ["note", ...]}
    "log": {},           # {"<id>": "YYYY-MM-DD"} completion dates
}


def load_data() -> dict:
    return json.loads(DATA_FILE.read_text())


def problems_by_id() -> dict[int, dict]:
    return {p["id"]: p for p in load_data()["problems"]}


def load_state() -> dict:
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
    else:
        state = {}
    # backfill any missing keys so the schema can evolve safely
    for k, v in DEFAULT_STATE.items():
        state.setdefault(k, json.loads(json.dumps(v)))
    return state


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def today_problem(data: dict, state: dict) -> dict | None:
    """Return tonight's problem, or None if the whole list (and review) is cleared.

    Phase 1 (main pass): lowest-id problem not in `done`.
    Phase 2 (review):   lowest-id flagged problem not yet in `review_done`.
    """
    done = set(state["done"])
    for p in data["problems"]:               # already in canonical topic order
        if p["id"] not in done:
            return p
    # main pass complete -> review the hard ones
    review_done = set(state["review_done"])
    flagged = [i for i in state["flagged"] if i not in review_done]
    if flagged:
        by_id = {p["id"]: p for p in data["problems"]}
        return by_id[min(flagged)]
    return None


def in_review_phase(data: dict, state: dict) -> bool:
    return len(state["done"]) >= len(data["problems"])


def mark_done(state: dict, pid: int, review: bool) -> None:
    today = dt.date.today().isoformat()
    if review:
        if pid not in state["review_done"]:
            state["review_done"].append(pid)
    else:
        if pid not in state["done"]:
            state["done"].append(pid)
    state["log"][str(pid)] = today


def flag(state: dict, pid: int) -> None:
    if pid not in state["flagged"]:
        state["flagged"].append(pid)


def add_note(state: dict, pid: int, text: str) -> None:
    state["notes"].setdefault(str(pid), []).append(text)


def notes_for(state: dict, pid: int) -> list[str]:
    return state["notes"].get(str(pid), [])


def streak(state: dict) -> int:
    """Consecutive days up to today with at least one completion."""
    days = {dt.date.fromisoformat(d) for d in state["log"].values()}
    if not days:
        return 0
    today = dt.date.today()
    # allow the streak to be "alive" if you did one today or yesterday
    if today not in days and (today - dt.timedelta(days=1)) not in days:
        return 0
    count = 0
    cur = today if today in days else today - dt.timedelta(days=1)
    while cur in days:
        count += 1
        cur -= dt.timedelta(days=1)
    return count


def topic_progress(data: dict, state: dict) -> list[dict]:
    done = set(state["done"])
    rows = {}
    for p in data["problems"]:
        t = p["topic"]
        rows.setdefault(t, {"topic": t, "done": 0, "total": 0})
        rows[t]["total"] += 1
        if p["id"] in done:
            rows[t]["done"] += 1
    # preserve roadmap order
    return [rows[t] for t in data["topics"]]

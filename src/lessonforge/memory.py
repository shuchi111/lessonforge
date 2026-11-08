"""Persistent memory (SQLite): runs, per-check results, learned rules, feedback, rubric proposals."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schemas import Attempt

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT,
    attempts INTEGER,
    first_attempt_passed INTEGER,
    writer_model TEXT,
    judge_model TEXT,
    rules_used TEXT,
    injected_errors TEXT
);
CREATE TABLE IF NOT EXISTS attempts (
    run_id TEXT NOT NULL,
    number INTEGER NOT NULL,
    lesson_md TEXT NOT NULL,
    changes TEXT,
    passed INTEGER,
    PRIMARY KEY (run_id, number)
);
CREATE TABLE IF NOT EXISTS check_results (
    run_id TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    check_id TEXT NOT NULL,
    name TEXT,
    method TEXT,
    passed INTEGER NOT NULL,
    reason TEXT,
    evidence TEXT,
    fix TEXT
);
CREATE TABLE IF NOT EXISTS learned_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule TEXT NOT NULL,
    source_check TEXT,
    created_at TEXT NOT NULL,
    created_by_run TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    times_applied INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS human_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL,
    processed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS rubric_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    criterion TEXT NOT NULL,
    rationale TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Memory:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        if str(path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def _rows(self, sql: str, args: tuple = ()) -> list[dict[str, Any]]:
        return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    # ---------- runs ----------
    def start_run(self, run_id: str, topic: str, writer: str, judge: str, rules: list[str]) -> None:
        self.conn.execute(
            "INSERT INTO runs (id, topic, started_at, writer_model, judge_model, rules_used) VALUES (?,?,?,?,?,?)",
            (run_id, topic, now(), writer, judge, json.dumps(rules)),
        )
        self.conn.commit()

    def finish_run(self, run_id: str, status: str, attempts: list[Attempt]) -> None:
        injected = sorted({e for a in attempts for e in a.injected_errors})
        self.conn.execute(
            "UPDATE runs SET finished_at=?, status=?, attempts=?, first_attempt_passed=?, injected_errors=? WHERE id=?",
            (now(), status, len(attempts), int(attempts[0].evaluation.passed), json.dumps(injected), run_id),
        )
        for a in attempts:
            self.conn.execute(
                "INSERT OR REPLACE INTO attempts (run_id, number, lesson_md, changes, passed) VALUES (?,?,?,?,?)",
                (run_id, a.number, a.lesson_md, a.changes, int(a.evaluation.passed)),
            )
            self.conn.execute("DELETE FROM check_results WHERE run_id=? AND attempt=?", (run_id, a.number))
            self.conn.executemany(
                "INSERT INTO check_results (run_id, attempt, check_id, name, method, passed, reason, evidence, fix) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                [(run_id, a.number, r.id, r.name, r.method, int(r.passed), r.reason, r.evidence, r.fix)
                 for r in a.evaluation.results],
            )
        self.conn.commit()

    def runs(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,))

    def run_attempts(self, run_id: str) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM attempts WHERE run_id=? ORDER BY number", (run_id,))

    def run_checks(self, run_id: str) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM check_results WHERE run_id=? ORDER BY attempt", (run_id,))

    # ---------- learning signals ----------
    def repeated_failures(self, min_runs: int, *, exclude_injected: bool = True) -> list[dict[str, Any]]:
        """Checks that failed in at least `min_runs` distinct runs (any attempt)."""
        injected_filter = "AND (r.injected_errors IS NULL OR r.injected_errors = '[]')" if exclude_injected else ""
        rows = self._rows(f"""
            SELECT c.check_id, c.name, COUNT(DISTINCT c.run_id) AS runs_failed
            FROM check_results c JOIN runs r ON r.id = c.run_id
            WHERE c.passed = 0 {injected_filter}
            GROUP BY c.check_id HAVING runs_failed >= ? ORDER BY runs_failed DESC
        """, (min_runs,))
        for row in rows:
            row["sample_reasons"] = [r["reason"] for r in self._rows(
                "SELECT reason FROM check_results WHERE check_id=? AND passed=0 ORDER BY rowid DESC LIMIT 3",
                (row["check_id"],))]
        return rows

    def check_pass_rates(self) -> list[dict[str, Any]]:
        return self._rows("""
            SELECT check_id, name, COUNT(*) AS total, SUM(passed) AS passed,
                   ROUND(100.0 * SUM(passed) / COUNT(*), 1) AS pass_rate
            FROM check_results GROUP BY check_id ORDER BY pass_rate ASC
        """)

    def first_attempt_pass_history(self) -> list[dict[str, Any]]:
        return self._rows("""
            SELECT r.id, r.started_at, r.status, r.attempts, r.first_attempt_passed,
                   (SELECT COUNT(*) FROM check_results c WHERE c.run_id=r.id AND c.attempt=1 AND c.passed=0) AS first_attempt_failures
            FROM runs r WHERE r.finished_at IS NOT NULL ORDER BY r.started_at
        """)

    # ---------- rules ----------
    def active_rules(self) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM learned_rules WHERE active=1 ORDER BY id")

    def all_rules(self) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM learned_rules ORDER BY id")

    def add_rule(self, rule: str, source_check: str, run_id: str | None, max_active: int) -> int:
        cur = self.conn.execute(
            "INSERT INTO learned_rules (rule, source_check, created_at, created_by_run) VALUES (?,?,?,?)",
            (rule, source_check, now(), run_id),
        )
        active = self.active_rules()
        for old in active[: max(0, len(active) - max_active)]:
            self.conn.execute("UPDATE learned_rules SET active=0 WHERE id=?", (old["id"],))
        self.conn.commit()
        return int(cur.lastrowid)

    def mark_rules_applied(self, ids: list[int]) -> None:
        self.conn.executemany("UPDATE learned_rules SET times_applied = times_applied + 1 WHERE id=?",
                              [(i,) for i in ids])
        self.conn.commit()

    def set_rule_active(self, rule_id: int, active: bool) -> None:
        self.conn.execute("UPDATE learned_rules SET active=? WHERE id=?", (int(active), rule_id))
        self.conn.commit()

    # ---------- human feedback ----------
    def add_feedback(self, run_id: str | None, note: str) -> int:
        cur = self.conn.execute("INSERT INTO human_feedback (run_id, note, created_at) VALUES (?,?,?)",
                                (run_id, note, now()))
        self.conn.commit()
        return int(cur.lastrowid)

    def unprocessed_feedback(self) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM human_feedback WHERE processed=0 ORDER BY id")

    def mark_feedback_processed(self, ids: list[int]) -> None:
        self.conn.executemany("UPDATE human_feedback SET processed=1 WHERE id=?", [(i,) for i in ids])
        self.conn.commit()

    # ---------- rubric evolution ----------
    def add_proposal(self, criterion: str, rationale: str) -> int:
        cur = self.conn.execute("INSERT INTO rubric_proposals (criterion, rationale, created_at) VALUES (?,?,?)",
                                (criterion, rationale, now()))
        self.conn.commit()
        return int(cur.lastrowid)

    def proposals(self, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            return self._rows("SELECT * FROM rubric_proposals WHERE status=? ORDER BY id", (status,))
        return self._rows("SELECT * FROM rubric_proposals ORDER BY id")

    def set_proposal_status(self, proposal_id: int, status: str) -> None:
        self.conn.execute("UPDATE rubric_proposals SET status=? WHERE id=?", (status, proposal_id))
        self.conn.commit()

    def approved_checks(self) -> list[dict[str, Any]]:
        """Human-approved proposals become extra LLM checks (X1, X2, ...) in the pedagogy judge."""
        return [
            {"id": f"X{p['id']}", "name": p["criterion"][:60], "dimension": "learned (human-approved)",
             "method": "llm", "judge": "pedagogy", "severity": "major", "criterion": p["criterion"]}
            for p in self.proposals("approved")
        ]

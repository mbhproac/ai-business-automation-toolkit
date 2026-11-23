"""Durable SQLite job queue with atomic claims, leases, audit events and deduplication."""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=15000")
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    dedup_key TEXT UNIQUE,
                    next_run_at TEXT NOT NULL,
                    lease_until TEXT,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS jobs_ready ON jobs(status, next_run_at);
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)

    def enqueue(self, workflow_id: str, payload: dict, dedup_key: str | None) -> dict:
        job_id, ts = str(uuid.uuid4()), now()
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if dedup_key:
                old = conn.execute("SELECT * FROM jobs WHERE dedup_key=?", (dedup_key,)).fetchone()
                if old:
                    conn.commit()
                    return dict(old)
            conn.execute(
                """INSERT INTO jobs
                (id,workflow_id,payload,status,dedup_key,next_run_at,created_at,updated_at)
                VALUES (?,?,?,'queued',?,?,?,?)""",
                (job_id, workflow_id, json.dumps(payload), dedup_key, ts, ts, ts),
            )
            conn.commit()
        return self.get(job_id)

    def get(self, job_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            return dict(row) if row else None

    def claim(self, lease_seconds: int) -> dict | None:
        ts = now()
        lease = (datetime.now(timezone.utc) + timedelta(seconds=lease_seconds)).isoformat(
            timespec="microseconds"
        )
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """SELECT * FROM jobs WHERE
                (status='queued' AND next_run_at<=?) OR
                (status='running' AND lease_until<=?)
                ORDER BY next_run_at,created_at LIMIT 1""",
                (ts, ts),
            ).fetchone()
            if not row:
                conn.commit()
                return None
            conn.execute(
                """UPDATE jobs SET status='running', attempts=attempts+1,
                lease_until=?, updated_at=? WHERE id=?""",
                (lease, ts, row["id"]),
            )
            conn.commit()
            return self.get(row["id"])

    def complete(self, job_id: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE jobs SET status='succeeded',lease_until=NULL,updated_at=? WHERE id=?",
                (now(), job_id),
            )

    def failed(self, job_id: str, error: str, max_retries: int) -> None:
        job = self.get(job_id)
        if not job:
            return
        retry = job["attempts"] < max_retries
        delay = min(300, 2 ** min(job["attempts"], 8))
        next_run = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat(
            timespec="microseconds"
        )
        with self.connect() as conn:
            conn.execute(
                """UPDATE jobs SET status=?,last_error=?,next_run_at=?,lease_until=NULL,
                updated_at=? WHERE id=?""",
                ("queued" if retry else "failed", error[:500], next_run, now(), job_id),
            )

    def event(self, job_id: str, kind: str, detail: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO events(job_id,kind,detail,created_at) VALUES (?,?,?,?)",
                (job_id, kind, detail[:1000], now()),
            )

    def events(self, job_id: str) -> list[dict]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT kind,detail,created_at FROM events WHERE job_id=? ORDER BY id", (job_id,)
            )]

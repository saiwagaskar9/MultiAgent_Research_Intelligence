"""
Database layer — SQLite persistent storage for research history.
"""
import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from config.settings import DB_PATH

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS research_sessions (
            id          TEXT PRIMARY KEY,
            topic       TEXT NOT NULL,
            depth       TEXT DEFAULT 'standard',
            mode        TEXT DEFAULT 'multi_agent',
            status      TEXT DEFAULT 'in_progress',
            created_at  TEXT NOT NULL,
            completed_at TEXT,
            quality_score INTEGER DEFAULT 0,
            execution_time REAL DEFAULT 0,
            total_agents  INTEGER DEFAULT 0,
            agent_calls   INTEGER DEFAULT 0,
            metadata    TEXT DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS research_reports (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL REFERENCES research_sessions(id),
            report_text TEXT NOT NULL,
            report_format TEXT DEFAULT 'markdown',
            created_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_communications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            timestamp   TEXT NOT NULL,
            sender      TEXT NOT NULL,
            recipient   TEXT NOT NULL,
            message_type TEXT NOT NULL,
            content     TEXT NOT NULL,
            metadata    TEXT DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS fact_checks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            claim       TEXT NOT NULL,
            status      TEXT NOT NULL,
            evidence    TEXT,
            confidence  REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS app_stats (
            id          INTEGER PRIMARY KEY CHECK (id = 1),
            total_reports    INTEGER DEFAULT 0,
            total_executions INTEGER DEFAULT 0,
            successful_tasks INTEGER DEFAULT 0,
            avg_quality_score REAL DEFAULT 0,
            last_updated TEXT
        );

        INSERT OR IGNORE INTO app_stats (id, total_reports, total_executions, successful_tasks, avg_quality_score, last_updated)
        VALUES (1, 0, 0, 0, 0.0, datetime('now'));
    """)
    conn.commit()
    conn.close()


def save_session(session_id: str, topic: str, depth: str, mode: str):
    conn = get_connection()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO research_sessions
               (id, topic, depth, mode, status, created_at)
               VALUES (?, ?, ?, ?, 'in_progress', ?)""",
            (session_id, topic, depth, mode, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def complete_session(
    session_id: str,
    quality_score: int,
    execution_time: float,
    total_agents: int,
    agent_calls: int,
    metadata: dict = None,
):
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE research_sessions
               SET status='completed', completed_at=?, quality_score=?,
                   execution_time=?, total_agents=?, agent_calls=?, metadata=?
               WHERE id=?""",
            (
                datetime.now().isoformat(),
                quality_score,
                round(execution_time, 2),
                total_agents,
                agent_calls,
                json.dumps(metadata or {}),
                session_id,
            ),
        )
        # Update global stats
        conn.execute(
            """UPDATE app_stats SET
               total_reports    = total_reports + 1,
               total_executions = total_executions + ?,
               successful_tasks = successful_tasks + 1,
               avg_quality_score = (avg_quality_score * total_reports + ?) / (total_reports + 1),
               last_updated = datetime('now')
               WHERE id = 1""",
            (agent_calls, quality_score),
        )
        conn.commit()
    finally:
        conn.close()


def save_report(session_id: str, report_text: str, report_format: str = "markdown"):
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO research_reports (session_id, report_text, report_format, created_at)
               VALUES (?, ?, ?, ?)""",
            (session_id, report_text, report_format, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def save_messages(session_id: str, messages: list):
    conn = get_connection()
    try:
        for msg in messages:
            conn.execute(
                """INSERT INTO agent_communications
                   (session_id, timestamp, sender, recipient, message_type, content, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    msg.timestamp,
                    msg.sender,
                    msg.recipient,
                    msg.message_type.value if hasattr(msg.message_type, "value") else msg.message_type,
                    msg.content,
                    json.dumps(msg.metadata),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def save_fact_checks(session_id: str, fact_checks: list):
    conn = get_connection()
    try:
        for fc in fact_checks:
            conn.execute(
                """INSERT INTO fact_checks (session_id, claim, status, evidence, confidence)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, fc.claim, fc.status, fc.evidence, fc.confidence),
            )
        conn.commit()
    finally:
        conn.close()


def get_all_sessions() -> List[Dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT s.*, r.report_text
               FROM research_sessions s
               LEFT JOIN research_reports r ON r.session_id = s.id
               ORDER BY s.created_at DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_session_report(session_id: str) -> Optional[str]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT report_text FROM research_reports WHERE session_id=? ORDER BY id DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        return row["report_text"] if row else None
    finally:
        conn.close()


def get_app_stats() -> Dict:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM app_stats WHERE id=1").fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def delete_session(session_id: str):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM research_reports WHERE session_id=?", (session_id,))
        conn.execute("DELETE FROM agent_communications WHERE session_id=?", (session_id,))
        conn.execute("DELETE FROM fact_checks WHERE session_id=?", (session_id,))
        conn.execute("DELETE FROM research_sessions WHERE id=?", (session_id,))
        conn.commit()
    finally:
        conn.close()


# Initialize on import
initialize_db()


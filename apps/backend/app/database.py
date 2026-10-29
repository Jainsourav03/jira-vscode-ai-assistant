import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jira_assistant.db")
)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db():
    """Initializes tables and indexes in the SQLite database."""
    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    key TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'To Do',
                    priority TEXT DEFAULT 'Medium',
                    url TEXT,
                    assignee_email TEXT,
                    assignee_name TEXT,
                    project_key TEXT,
                    comments_json TEXT DEFAULT '[]',
                    raw_data_json TEXT DEFAULT '{}',
                    created_at TEXT,
                    updated_at TEXT
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS developer_contexts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_key TEXT NOT NULL,
                    user_email TEXT NOT NULL,
                    additional_context TEXT NOT NULL,
                    repo_path TEXT,
                    active_file TEXT,
                    branch_name TEXT,
                    notes TEXT,
                    submitted_at TEXT NOT NULL,
                    FOREIGN KEY (ticket_key) REFERENCES tickets(key) ON DELETE CASCADE
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_key TEXT NOT NULL,
                    prompt TEXT,
                    analysis_result TEXT NOT NULL,
                    provider TEXT,
                    model TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (ticket_key) REFERENCES tickets(key) ON DELETE CASCADE
                );
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_dev_context_ticket ON developer_contexts(ticket_key);
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_analysis_ticket ON ai_analyses(ticket_key);
            """)

        logger.info(f"Database initialized successfully at {DB_PATH}")
        seed_initial_data()
    finally:
        conn.close()


def seed_initial_data():
    """Seeds a realistic default ticket if database has no tickets."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tickets;")
        count = cursor.fetchone()[0]
        if count == 0:
            now = datetime.now().isoformat()
            sample_ticket = {
                "key": "PROJ-101",
                "title": "OAuth2 Token Refresh Redirect Loop in Auth Flow",
                "description": (
                    "When a user session expires while navigating protected dashboard routes, "
                    "the silent token refresh fails with 401 and enters an infinite redirect loop "
                    "between /login and /oauth/callback. Need to catch the expired refresh token error, "
                    "clear stale localStorage session tokens, and route to /login with ?sessionExpired=true."
                ),
                "status": "In Progress",
                "priority": "High",
                "url": "https://jira.example.com/browse/PROJ-101",
                "assignee_email": "developer@example.com",
                "assignee_name": "Dev Engineer",
                "project_key": "PROJ",
                "comments": [
                    "QA reproduced on Chrome 120 and Safari iOS.",
                    "Backend auth service logs show expired refresh token returns 401 Unauthorized."
                ]
            }
            upsert_ticket(sample_ticket)
            logger.info("Database seeded with initial realistic Jira ticket PROJ-101")
    finally:
        conn.close()


def upsert_ticket(data: Dict[str, Any]) -> Dict[str, Any]:
    """Inserts or updates a Jira ticket in the database."""
    now = datetime.now().isoformat()
    ticket_key = data.get("ticket_key") or data.get("key")
    if not ticket_key:
        raise ValueError("Ticket key is required")

    comments = data.get("comments", [])
    if isinstance(comments, list):
        comments_json = json.dumps(comments)
    else:
        comments_json = "[]"

    conn = get_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO tickets (
                    key, title, description, status, priority, url,
                    assignee_email, assignee_name, project_key,
                    comments_json, raw_data_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    title = excluded.title,
                    description = excluded.description,
                    status = excluded.status,
                    priority = excluded.priority,
                    url = excluded.url,
                    assignee_email = excluded.assignee_email,
                    assignee_name = excluded.assignee_name,
                    project_key = excluded.project_key,
                    comments_json = excluded.comments_json,
                    raw_data_json = excluded.raw_data_json,
                    updated_at = excluded.updated_at;
            """, (
                ticket_key,
                data.get("ticket_title") or data.get("title") or "Untitled Ticket",
                data.get("ticket_description") or data.get("description") or "",
                data.get("ticket_status") or data.get("status") or "To Do",
                data.get("ticket_priority") or data.get("priority") or "Medium",
                data.get("ticket_url") or data.get("url") or f"https://jira.atlassian.com/browse/{ticket_key}",
                data.get("assignee_email") or data.get("assigneeEmail") or "developer@example.com",
                data.get("assignee_name") or data.get("assigneeName") or "Developer",
                data.get("project_key") or data.get("projectKey") or ticket_key.split("-")[0] if "-" in ticket_key else "",
                comments_json,
                json.dumps(data.get("raw_data", {})),
                data.get("created_at") or now,
                now
            ))
        return get_ticket(ticket_key)
    finally:
        conn.close()


def get_ticket(ticket_key: str) -> Optional[Dict[str, Any]]:
    """Retrieves a ticket by key."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE key = ?", (ticket_key,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["comments"] = json.loads(d.get("comments_json") or "[]")
        except Exception:
            d["comments"] = []
        return d
    finally:
        conn.close()


def get_all_tickets(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves recent tickets from the database."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets ORDER BY updated_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            try:
                d["comments"] = json.loads(d.get("comments_json") or "[]")
            except Exception:
                d["comments"] = []
            results.append(d)
        return results
    finally:
        conn.close()


def insert_developer_context(data: Dict[str, Any]) -> Dict[str, Any]:
    """Stores developer context for a ticket."""
    now = datetime.now().isoformat()
    ticket_key = data.get("ticketKey") or data.get("ticket_key")
    if not ticket_key:
        raise ValueError("ticket_key is required")

    # Ensure ticket exists first so foreign key doesn't fail
    if not get_ticket(ticket_key):
        upsert_ticket({
            "key": ticket_key,
            "title": f"Jira Issue {ticket_key}",
            "description": "Auto-created from developer context submission",
            "assignee_email": data.get("userEmail", "developer@example.com")
        })

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO developer_contexts (
                    ticket_key, user_email, additional_context,
                    repo_path, active_file, branch_name, notes, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                ticket_key,
                data.get("userEmail") or data.get("user_email") or "developer@example.com",
                data.get("additionalContext") or data.get("additional_context") or "",
                data.get("repoPath") or data.get("repo_path"),
                data.get("activeFile") or data.get("active_file"),
                data.get("branchName") or data.get("branch_name"),
                data.get("notes"),
                data.get("submittedAt") or now
            ))
            context_id = cursor.lastrowid

        return {
            "id": context_id,
            "ticketKey": ticket_key,
            "userEmail": data.get("userEmail") or data.get("user_email"),
            "additionalContext": data.get("additionalContext") or data.get("additional_context"),
            "repoPath": data.get("repoPath") or data.get("repo_path"),
            "activeFile": data.get("activeFile") or data.get("active_file"),
            "branchName": data.get("branchName") or data.get("branch_name"),
            "notes": data.get("notes"),
            "submittedAt": now
        }
    finally:
        conn.close()


def get_developer_contexts(ticket_key: str) -> List[Dict[str, Any]]:
    """Retrieves all developer context submissions for a ticket."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM developer_contexts WHERE ticket_key = ? ORDER BY id DESC",
            (ticket_key,)
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def insert_ai_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    """Stores an AI analysis result in the database."""
    now = datetime.now().isoformat()
    ticket_key = data.get("ticket_key")
    if not ticket_key:
        raise ValueError("ticket_key is required")

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_analyses (
                    ticket_key, prompt, analysis_result, provider, model, created_at
                ) VALUES (?, ?, ?, ?, ?, ?);
            """, (
                ticket_key,
                data.get("prompt", ""),
                data.get("analysis_result", ""),
                data.get("provider", "openai"),
                data.get("model", "default"),
                now
            ))
            analysis_id = cursor.lastrowid
        return {
            "id": analysis_id,
            "ticketKey": ticket_key,
            "analysisResult": data.get("analysis_result"),
            "provider": data.get("provider"),
            "model": data.get("model"),
            "createdAt": now
        }
    finally:
        conn.close()


def get_ai_analyses(ticket_key: str) -> List[Dict[str, Any]]:
    """Retrieves all AI analyses stored for a ticket."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM ai_analyses WHERE ticket_key = ? ORDER BY id DESC",
            (ticket_key,)
        )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

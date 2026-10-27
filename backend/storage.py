"""SQLite persistence for anonymous local STOP practice sessions."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "app.sqlite3"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(db_path: Path = DEFAULT_DB_PATH) -> None:
    with connect(db_path) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS skill_sessions (
                session_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL UNIQUE
                    REFERENCES conversations(conversation_id) ON DELETE CASCADE,
                skill TEXT NOT NULL CHECK (skill = 'STOP'),
                status TEXT NOT NULL CHECK (status IN ('in_progress', 'completed', 'left')),
                current_step INTEGER NOT NULL DEFAULT 1 CHECK (current_step BETWEEN 1 AND 4),
                started_at TEXT NOT NULL,
                ended_at TEXT,
                duration_seconds INTEGER CHECK (duration_seconds IS NULL OR duration_seconds >= 0)
            );

            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL
                    REFERENCES conversations(conversation_id) ON DELETE CASCADE,
                session_id TEXT NOT NULL
                    REFERENCES skill_sessions(session_id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 2000),
                request_status TEXT NOT NULL CHECK (request_status IN ('complete', 'failed')),
                model_source TEXT CHECK (model_source IS NULL OR model_source IN ('demo', 'openai')),
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS breathing_sessions (
                session_id TEXT PRIMARY KEY,
                skill TEXT NOT NULL DEFAULT 'paced_breathing'
                    CHECK (skill = 'paced_breathing'),
                status TEXT NOT NULL CHECK (status IN ('in_progress', 'completed', 'left')),
                started_at TEXT NOT NULL,
                ended_at TEXT,
                duration_seconds INTEGER CHECK (duration_seconds IS NULL OR duration_seconds >= 0)
            );

            CREATE TABLE IF NOT EXISTS mood_checkins (
                checkin_id TEXT PRIMARY KEY,
                mood TEXT NOT NULL CHECK (mood IN ('low', 'steady', 'good')),
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS profile_preferences (
                profile_id TEXT PRIMARY KEY CHECK (profile_id = 'local-demo'),
                default_skill TEXT NOT NULL CHECK (default_skill IN ('STOP', 'paced_breathing')),
                animate_breathing INTEGER NOT NULL CHECK (animate_breathing IN (0, 1)),
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL UNIQUE
                    REFERENCES conversations(conversation_id) ON DELETE CASCADE,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                message_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL
                    REFERENCES conversations(conversation_id) ON DELETE CASCADE,
                session_id TEXT NOT NULL
                    REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 2000),
                request_status TEXT NOT NULL CHECK (request_status IN ('complete', 'failed')),
                model_source TEXT CHECK (model_source IS NULL OR model_source IN ('demo', 'openai')),
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS ix_sessions_started_at
                ON skill_sessions(started_at DESC);
            CREATE INDEX IF NOT EXISTS ix_messages_conversation_time
                ON messages(conversation_id, created_at, message_id);
            CREATE INDEX IF NOT EXISTS ix_breathing_started_at
                ON breathing_sessions(started_at DESC);
            CREATE INDEX IF NOT EXISTS ix_checkins_created_at
                ON mood_checkins(created_at DESC);
            CREATE INDEX IF NOT EXISTS ix_chat_messages_time
                ON chat_messages(session_id, created_at, message_id);
            """
        )


def begin_session(db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    session_id = str(uuid4())
    conversation_id = str(uuid4())
    started_at = utc_now()
    with connect(db_path) as db:
        db.execute(
            "INSERT INTO conversations (conversation_id, created_at) VALUES (?, ?)",
            (conversation_id, started_at),
        )
        db.execute(
            """INSERT INTO skill_sessions
               (session_id, conversation_id, skill, status, current_step, started_at)
               VALUES (?, ?, 'STOP', 'in_progress', 1, ?)""",
            (session_id, conversation_id, started_at),
        )
    return {
        "session_id": session_id,
        "conversation_id": conversation_id,
        "skill": "STOP",
        "status": "in_progress",
        "current_step": 1,
        "started_at": started_at,
    }


def get_session(session_id: str, db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Row | None:
    with connect(db_path) as db:
        return db.execute(
            "SELECT * FROM skill_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()


def set_step(session_id: str, step: int, db_path: Path = DEFAULT_DB_PATH) -> bool:
    with connect(db_path) as db:
        result = db.execute(
            """UPDATE skill_sessions SET current_step = ?
               WHERE session_id = ? AND status = 'in_progress'""",
            (step, session_id),
        )
        return result.rowcount == 1


def add_user_message(session_id: str, content: str, db_path: Path = DEFAULT_DB_PATH) -> str:
    message_id = str(uuid4())
    created_at = utc_now()
    with connect(db_path) as db:
        session = db.execute(
            "SELECT conversation_id, status FROM skill_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if not session or session["status"] != "in_progress":
            raise ValueError("Session is not active")
        db.execute(
            """INSERT INTO messages
               (message_id, conversation_id, session_id, role, content, request_status, created_at)
               VALUES (?, ?, ?, 'user', ?, 'complete', ?)""",
            (message_id, session["conversation_id"], session_id, content, created_at),
        )
    return message_id


def mark_request_failed(message_id: str, db_path: Path = DEFAULT_DB_PATH) -> None:
    # The user turn remains visible; a fabricated assistant reply is never inserted.
    with connect(db_path) as db:
        db.execute(
            "UPDATE messages SET request_status = 'failed' WHERE message_id = ? AND role = 'user'",
            (message_id,),
        )


def get_model_history(session_id: str, db_path: Path = DEFAULT_DB_PATH) -> list[sqlite3.Row]:
    with connect(db_path) as db:
        return db.execute(
            """SELECT role, content FROM messages
               WHERE session_id = ? AND request_status = 'complete'
               ORDER BY rowid DESC LIMIT 8""",
            (session_id,),
        ).fetchall()[::-1]


def add_assistant_message(
    session_id: str,
    content: str,
    model_source: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> str:
    message_id = str(uuid4())
    created_at = utc_now()
    with connect(db_path) as db:
        session = db.execute(
            "SELECT conversation_id, status FROM skill_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if not session or session["status"] != "in_progress":
            raise ValueError("Session is not active")
        db.execute(
            """INSERT INTO messages
               (message_id, conversation_id, session_id, role, content, request_status, model_source, created_at)
               VALUES (?, ?, ?, 'assistant', ?, 'complete', ?, ?)""",
            (message_id, session["conversation_id"], session_id, content, model_source, created_at),
        )
    return message_id


def finish_session(
    session_id: str,
    status: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any] | None:
    if status not in {"completed", "left"}:
        raise ValueError("Invalid session status")
    ended_at = utc_now()
    with connect(db_path) as db:
        session = db.execute(
            "SELECT * FROM skill_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not session:
            return None
        if session["status"] == "in_progress":
            started = datetime.fromisoformat(session["started_at"].replace("Z", "+00:00"))
            ended = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
            duration = max(0, int((ended - started).total_seconds()))
            db.execute(
                """UPDATE skill_sessions
                   SET status = ?, ended_at = ?, duration_seconds = ?
                   WHERE session_id = ? AND status = 'in_progress'""",
                (status, ended_at, duration, session_id),
            )
        row = db.execute(
            "SELECT * FROM skill_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        return dict(row)


def list_history(limit: int = 10, db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    with connect(db_path) as db:
        sessions = db.execute(
            """SELECT s.*, c.created_at AS conversation_created_at
               FROM skill_sessions s
               JOIN conversations c USING (conversation_id)
               ORDER BY s.started_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        result: list[dict[str, Any]] = []
        for session in sessions:
            item = dict(session)
            item["messages"] = [
                dict(message)
                for message in db.execute(
                    """SELECT message_id, role, content, request_status, model_source, created_at
                       FROM messages WHERE session_id = ?
                       ORDER BY rowid""",
                    (session["session_id"],),
                ).fetchall()
            ]
            result.append(item)
        breathing = db.execute(
            "SELECT * FROM breathing_sessions ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        result.extend({**dict(item), "conversation_id": None, "current_step": None, "messages": []}
                      for item in breathing)
        result.sort(key=lambda item: item["started_at"], reverse=True)
        return result[:limit]


def begin_breathing_session(db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    session_id = str(uuid4())
    started_at = utc_now()
    with connect(db_path) as db:
        db.execute(
            "INSERT INTO breathing_sessions (session_id, status, started_at) VALUES (?, 'in_progress', ?)",
            (session_id, started_at),
        )
    return {"session_id": session_id, "skill": "paced_breathing", "status": "in_progress", "started_at": started_at}


def finish_breathing_session(session_id: str, status: str, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    if status not in {"completed", "left"}:
        raise ValueError("Invalid session status")
    ended_at = utc_now()
    with connect(db_path) as db:
        session = db.execute("SELECT * FROM breathing_sessions WHERE session_id = ?", (session_id,)).fetchone()
        if not session:
            return None
        if session["status"] == "in_progress":
            started = datetime.fromisoformat(session["started_at"].replace("Z", "+00:00"))
            ended = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
            duration = max(0, int((ended - started).total_seconds()))
            db.execute(
                "UPDATE breathing_sessions SET status = ?, ended_at = ?, duration_seconds = ? WHERE session_id = ? AND status = 'in_progress'",
                (status, ended_at, duration, session_id),
            )
        return dict(db.execute("SELECT * FROM breathing_sessions WHERE session_id = ?", (session_id,)).fetchone())


def add_mood_checkin(mood: str, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    if mood not in {"low", "steady", "good"}:
        raise ValueError("Invalid mood")
    item = {"checkin_id": str(uuid4()), "mood": mood, "created_at": utc_now()}
    with connect(db_path) as db:
        db.execute("INSERT INTO mood_checkins (checkin_id, mood, created_at) VALUES (?, ?, ?)",
                   (item["checkin_id"], mood, item["created_at"]))
    return item


def list_mood_checkins(limit: int = 100, db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    with connect(db_path) as db:
        return [dict(row) for row in db.execute(
            "SELECT * FROM mood_checkins ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()]


def delete_mood_checkin(checkin_id: str, db_path: Path = DEFAULT_DB_PATH) -> bool:
    with connect(db_path) as db:
        return db.execute("DELETE FROM mood_checkins WHERE checkin_id = ?", (checkin_id,)).rowcount == 1


def get_profile_preferences(db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    with connect(db_path) as db:
        row = db.execute("SELECT * FROM profile_preferences WHERE profile_id = 'local-demo'").fetchone()
        if row:
            return {"default_skill": row["default_skill"], "animate_breathing": bool(row["animate_breathing"])}
        return {"default_skill": "paced_breathing", "animate_breathing": True}


def save_profile_preferences(default_skill: str, animate_breathing: bool, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    if default_skill not in {"STOP", "paced_breathing"}:
        raise ValueError("Invalid default skill")
    updated_at = utc_now()
    with connect(db_path) as db:
        db.execute(
            "INSERT INTO profile_preferences (profile_id, default_skill, animate_breathing, updated_at) VALUES ('local-demo', ?, ?, ?) ON CONFLICT(profile_id) DO UPDATE SET default_skill = excluded.default_skill, animate_breathing = excluded.animate_breathing, updated_at = excluded.updated_at",
            (default_skill, int(animate_breathing), updated_at),
        )
    return {"default_skill": default_skill, "animate_breathing": animate_breathing}


def begin_chat_session(db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    session_id = str(uuid4())
    conversation_id = str(uuid4())
    created_at = utc_now()
    with connect(db_path) as db:
        db.execute("INSERT INTO conversations (conversation_id, created_at) VALUES (?, ?)",
                   (conversation_id, created_at))
        db.execute("INSERT INTO chat_sessions (session_id, conversation_id, created_at) VALUES (?, ?, ?)",
                   (session_id, conversation_id, created_at))
    return {"session_id": session_id, "conversation_id": conversation_id, "created_at": created_at}


def add_chat_user_message(session_id: str, content: str, db_path: Path = DEFAULT_DB_PATH) -> str:
    message_id = str(uuid4())
    created_at = utc_now()
    with connect(db_path) as db:
        session = db.execute("SELECT conversation_id FROM chat_sessions WHERE session_id = ?",
                             (session_id,)).fetchone()
        if not session:
            raise ValueError("Chat session not found")
        db.execute(
            """INSERT INTO chat_messages
               (message_id, conversation_id, session_id, role, content, request_status, created_at)
               VALUES (?, ?, ?, 'user', ?, 'complete', ?)""",
            (message_id, session["conversation_id"], session_id, content, created_at),
        )
    return message_id


def mark_chat_request_failed(message_id: str, db_path: Path = DEFAULT_DB_PATH) -> None:
    with connect(db_path) as db:
        db.execute("UPDATE chat_messages SET request_status = 'failed' WHERE message_id = ? AND role = 'user'",
                   (message_id,))


def get_chat_model_history(session_id: str, db_path: Path = DEFAULT_DB_PATH) -> list[sqlite3.Row]:
    with connect(db_path) as db:
        return db.execute(
            """SELECT role, content FROM chat_messages
               WHERE session_id = ? AND request_status = 'complete'
               ORDER BY rowid DESC LIMIT 8""",
            (session_id,),
        ).fetchall()[::-1]


def add_chat_assistant_message(
    session_id: str, content: str, model_source: str, db_path: Path = DEFAULT_DB_PATH
) -> str:
    message_id = str(uuid4())
    created_at = utc_now()
    with connect(db_path) as db:
        session = db.execute("SELECT conversation_id FROM chat_sessions WHERE session_id = ?",
                             (session_id,)).fetchone()
        if not session:
            raise ValueError("Chat session not found")
        db.execute(
            """INSERT INTO chat_messages
               (message_id, conversation_id, session_id, role, content, request_status, model_source, created_at)
               VALUES (?, ?, ?, 'assistant', ?, 'complete', ?, ?)""",
            (message_id, session["conversation_id"], session_id, content, model_source, created_at),
        )
    return message_id


def list_chat_sessions(limit: int = 10, db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    with connect(db_path) as db:
        sessions = db.execute("SELECT * FROM chat_sessions ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        result = []
        for session in sessions:
            item = dict(session)
            item["messages"] = [dict(message) for message in db.execute(
                """SELECT message_id, role, content, request_status, model_source, created_at
                   FROM chat_messages WHERE session_id = ? ORDER BY rowid LIMIT 100""",
                (session["session_id"],),
            ).fetchall()]
            result.append(item)
        return result

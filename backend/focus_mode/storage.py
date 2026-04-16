import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class FocusModeStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS focus_mode_sessions (
                    session_id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    exam_id TEXT,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    last_heartbeat TEXT NOT NULL,
                    blocked_domains TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def create_session(
        self,
        session_id: str,
        student_id: str,
        exam_id: str | None,
        source: str,
        blocked_domains: list[str],
        metadata: dict,
    ) -> None:
        now = utcnow_iso()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO focus_mode_sessions (
                    session_id,
                    student_id,
                    exam_id,
                    source,
                    status,
                    started_at,
                    ended_at,
                    last_heartbeat,
                    blocked_domains,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    student_id,
                    exam_id,
                    source,
                    "active",
                    now,
                    None,
                    now,
                    json.dumps(blocked_domains),
                    json.dumps(metadata),
                ),
            )
            connection.commit()

    def update_heartbeat(self, session_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE focus_mode_sessions
                SET last_heartbeat = ?
                WHERE session_id = ? AND status = 'active'
                """,
                (utcnow_iso(), session_id),
            )
            connection.commit()
            return cursor.rowcount > 0

    def end_session(self, session_id: str, metadata: dict | None = None) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT metadata_json FROM focus_mode_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if not row:
                return False
            merged_metadata = json.loads(row["metadata_json"] or "{}")
            if metadata:
                merged_metadata.update(metadata)
            cursor = connection.execute(
                """
                UPDATE focus_mode_sessions
                SET status = 'ended',
                    ended_at = ?,
                    metadata_json = ?
                WHERE session_id = ? AND status = 'active'
                """,
                (utcnow_iso(), json.dumps(merged_metadata), session_id),
            )
            connection.commit()
            return cursor.rowcount > 0

    def get_session(self, session_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM focus_mode_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return self._row_to_dict(row)

    def get_active_session(self, student_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM focus_mode_sessions
                WHERE student_id = ? AND status = 'active'
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (student_id,),
            ).fetchone()
        return self._row_to_dict(row)

    def list_active_sessions(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM focus_mode_sessions
                WHERE status = 'active'
                ORDER BY started_at DESC
                """
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    @staticmethod
    def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        return {
            "session_id": row["session_id"],
            "student_id": row["student_id"],
            "exam_id": row["exam_id"],
            "source": row["source"],
            "status": row["status"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "last_heartbeat": row["last_heartbeat"],
            "blocked_domains": json.loads(row["blocked_domains"] or "[]"),
            "metadata": json.loads(row["metadata_json"] or "{}"),
        }

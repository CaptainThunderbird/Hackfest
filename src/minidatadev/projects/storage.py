"""Local SQLite-backed persistence for beta projects and conversations."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ProjectRecord:
    id: str
    owner: str
    name: str
    dataset_name: str
    data_path: str
    created_at: str
    updated_at: str


class ProjectStore:
    """Persist projects locally without requiring a hosted account service."""

    def __init__(self, database_path: Path, data_dir: Path) -> None:
        self.database_path = Path(database_path)
        self.data_dir = Path(data_dir)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL,
                    dataset_name TEXT NOT NULL, data_path TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL, role TEXT NOT NULL,
                    content TEXT NOT NULL, artifact_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_projects_owner
                    ON projects(owner, updated_at);
                """
            )

    def save_project(
        self,
        *,
        owner: str,
        name: str,
        dataset_name: str,
        frame: pd.DataFrame,
        messages: list[dict[str, Any]],
        project_id: str | None = None,
    ) -> str:
        project_id = project_id or uuid.uuid4().hex
        now = datetime.now(UTC).isoformat()
        data_path = self.data_dir / f"{project_id}.csv"
        frame.to_csv(data_path, index=False)
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT created_at FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            created_at = existing["created_at"] if existing else now
            connection.execute(
                """
                INSERT OR REPLACE INTO projects
                (id, owner, name, dataset_name, data_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    owner.strip() or "Local user",
                    name.strip() or dataset_name,
                    dataset_name,
                    str(data_path),
                    created_at,
                    now,
                ),
            )
            connection.execute(
                "DELETE FROM conversations WHERE project_id = ?", (project_id,)
            )
            for message in messages:
                artifact = _json_safe_artifact(message.get("artifact"))
                connection.execute(
                    """
                    INSERT INTO conversations
                    (project_id, role, content, artifact_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        str(message.get("role", "assistant")),
                        str(message.get("content", "")),
                        json.dumps(artifact, default=str) if artifact else None,
                        now,
                    ),
                )
        return project_id

    def list_projects(self, owner: str) -> list[ProjectRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM projects WHERE owner = ?
                ORDER BY updated_at DESC
                """,
                (owner.strip() or "Local user",),
            ).fetchall()
        return [ProjectRecord(**dict(row)) for row in rows]

    def load_project(
        self, project_id: str
    ) -> tuple[ProjectRecord, pd.DataFrame, list[dict[str, Any]]]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            if row is None:
                raise KeyError("Project not found.")
            message_rows = connection.execute(
                """
                SELECT role, content, artifact_json FROM conversations
                WHERE project_id = ? ORDER BY id
                """,
                (project_id,),
            ).fetchall()
        record = ProjectRecord(**dict(row))
        frame = pd.read_csv(record.data_path)
        messages = [
            {
                "role": item["role"],
                "content": item["content"],
                "artifact": (
                    json.loads(item["artifact_json"])
                    if item["artifact_json"]
                    else None
                ),
            }
            for item in message_rows
        ]
        return record, frame, messages

    def delete_project(self, project_id: str) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT data_path FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            connection.execute(
                "DELETE FROM conversations WHERE project_id = ?", (project_id,)
            )
            connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        if row:
            Path(row["data_path"]).unlink(missing_ok=True)

    def purge_older_than(self, days: int) -> int:
        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id FROM projects WHERE updated_at < ?", (cutoff,)
            ).fetchall()
        for row in rows:
            self.delete_project(row["id"])
        return len(rows)


def _json_safe_artifact(artifact: Any) -> dict[str, Any] | None:
    if not isinstance(artifact, dict):
        return None
    return {
        "tool_name": artifact.get("tool_name"),
        "provenance": artifact.get("provenance", []),
        "assumptions": artifact.get("assumptions", []),
        "parameters": artifact.get("parameters", {}),
    }

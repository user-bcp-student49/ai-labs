from __future__ import annotations

import sqlite3
from typing import Any

SEED_TASKS = (
    (
        "Refactor login",
        "Separar responsabilidades en frontend",
        "TODO",
        "student",
        "HIGH",
    ),
    (
        "Review API",
        "Revisar seguridad de endpoints",
        "IN_PROGRESS",
        "student",
        "MEDIUM",
    ),
    (
        "Trainer notes",
        "Preparar retrospectiva",
        "TODO",
        "trainer",
        "LOW",
    ),
)

TASK_SELECT = (
    "SELECT id,title,description,status,owner,priority,created_at FROM tasks"
)


class TaskRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def initialize(self) -> None:
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS tasks ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "title TEXT NOT NULL, "
            "description TEXT NOT NULL, "
            "status TEXT NOT NULL, "
            "owner TEXT NOT NULL, "
            "priority TEXT NOT NULL, "
            "created_at TEXT NOT NULL)"
        )
        count = self._connection.execute(
            "SELECT COUNT(*) AS total FROM tasks"
        ).fetchone()["total"]
        if count == 0:
            self._seed_tasks()

    def list_tasks(self, owner: str) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            f"{TASK_SELECT} WHERE owner = ? ORDER BY id",
            (owner,),
        ).fetchall()
        return [dict(row) for row in rows]

    def create_task(
        self,
        title: str,
        description: str,
        status: str,
        owner: str,
        priority: str,
    ) -> dict[str, Any]:
        cursor = self._connection.execute(
            "INSERT INTO tasks(title,description,status,owner,priority,created_at) "
            "VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (title, description, status, owner, priority),
        )
        self._connection.commit()
        row = self._connection.execute(
            f"{TASK_SELECT} WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        if row is None:
            raise RuntimeError("Created task could not be retrieved")
        return dict(row)

    def task_summary_rows(self, owner: str) -> list[sqlite3.Row]:
        return self._connection.execute(
            "SELECT status,priority FROM tasks WHERE owner = ?",
            (owner,),
        ).fetchall()

    def close(self) -> None:
        self._connection.close()

    def _seed_tasks(self) -> None:
        self._connection.executemany(
            "INSERT INTO tasks(title,description,status,owner,priority,created_at) "
            "VALUES (?, ?, ?, ?, ?, datetime('now'))",
            SEED_TASKS,
        )
        self._connection.commit()

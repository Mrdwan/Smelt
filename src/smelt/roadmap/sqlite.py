import sqlite3

from smelt.exceptions import StepNotFoundError, StorageError
from smelt.roadmap.base import RoadmapStorage, Step


class SQLiteRoadmapStorage(RoadmapStorage):
    def __init__(self, path: str):
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._create_table_if_not_exists()

    def _create_table_if_not_exists(self) -> None:
        try:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT NOT NULL,
                    done BOOLEAN NOT NULL DEFAULT 0
                )
                """
            )
            self._conn.commit()
        except sqlite3.Error as e:
            raise StorageError("Failed to create steps table") from e

    def close(self) -> None:
        self._conn.close()

    def add_step(self, description: str) -> str:
        try:
            cursor = self._conn.execute(
                "INSERT INTO steps (description) VALUES (?)", (description,)
            )
            self._conn.commit()
            return str(cursor.lastrowid)
        except sqlite3.Error as e:
            raise StorageError("Failed to add step") from e

    def next_step(self) -> Step | None:
        try:
            row = self._conn.execute(
                "SELECT id, description, done FROM steps WHERE done = 0 ORDER BY id LIMIT 1"
            ).fetchone()
            if row:
                return Step(
                    id=str(row["id"]),
                    description=row["description"],
                    done=bool(row["done"]),
                )
            return None
        except sqlite3.Error as e:
            raise StorageError("Failed to fetch next step") from e

    def mark_done(self, step_id: str) -> None:
        try:
            cursor = self._conn.execute(
                "UPDATE steps SET done = 1 WHERE id = ?", (step_id,)
            )
            self._conn.commit()

            if cursor.rowcount == 0:
                raise StepNotFoundError(f"No step found with id {step_id}")
        except sqlite3.Error as e:
            raise StorageError("Failed to mark step as done.") from e

    def all_steps(self) -> list[Step]:
        try:
            rows = self._conn.execute(
                "SELECT id, description, done FROM steps ORDER BY id"
            ).fetchall()
            return [
                Step(
                    id=str(row["id"]),
                    description=row["description"],
                    done=bool(row["done"]),
                )
                for row in rows
            ]
        except sqlite3.Error as e:
            raise StorageError("Failed to fetch all steps.") from e

from collections.abc import Iterator

import pytest

from smelt.exceptions import StepNotFoundError, StorageError
from smelt.roadmap.sqlite import SQLiteRoadmapStorage


@pytest.fixture
def roadmap() -> Iterator[SQLiteRoadmapStorage]:
    storage = SQLiteRoadmapStorage(":memory:")
    yield storage
    storage.close()


def test_sqlite_add_step_success(roadmap: SQLiteRoadmapStorage) -> None:
    roadmap.add_step("Test step 1")
    step = roadmap.next_step()
    assert step is not None
    assert step.description == "Test step 1"


def test_sqlite_mark_done_success(roadmap: SQLiteRoadmapStorage) -> None:
    step_id = roadmap.add_step("Test step 2")
    roadmap.mark_done(step_id)
    step = roadmap.next_step()
    assert step is None


def test_sqlite_next_step_no_steps(roadmap: SQLiteRoadmapStorage) -> None:
    step = roadmap.next_step()
    assert step is None


def test_sqlite_next_step_all_done(roadmap: SQLiteRoadmapStorage) -> None:
    roadmap.add_step("Test step 3")
    roadmap.mark_done("1")
    step = roadmap.next_step()
    assert step is None


def test_sqlite_next_step_multiple_steps(roadmap: SQLiteRoadmapStorage) -> None:
    roadmap.add_step("Test step 4")
    roadmap.add_step("Test step 5")
    step = roadmap.next_step()
    assert step is not None
    assert step.description == "Test step 4"
    roadmap.mark_done(step.id)
    step = roadmap.next_step()
    assert step is not None
    assert step.description == "Test step 5"


def test_sqlite_add_step_failure(roadmap: SQLiteRoadmapStorage) -> None:
    with pytest.raises(StorageError):
        roadmap._conn.execute("DROP TABLE steps")
        roadmap.add_step("This should fail")


def test_sqlite_mark_done_failure(roadmap: SQLiteRoadmapStorage) -> None:
    with pytest.raises(StorageError):
        roadmap._conn.execute("DROP TABLE steps")
        roadmap.mark_done("1")


def test_sqlite_next_step_failure(roadmap: SQLiteRoadmapStorage) -> None:
    with pytest.raises(StorageError):
        roadmap._conn.execute("DROP TABLE steps")
        roadmap.next_step()


def test_sqlite_close(roadmap: SQLiteRoadmapStorage) -> None:
    roadmap.close()
    with pytest.raises(StorageError):
        roadmap.add_step("This should fail after close")


def test_all_steps(roadmap: SQLiteRoadmapStorage) -> None:
    roadmap.add_step("Step 1")
    roadmap.add_step("Step 2")
    roadmap.mark_done("1")
    steps = roadmap.all_steps()
    assert len(steps) == 2
    assert steps[0].description == "Step 1"
    assert steps[0].done is True
    assert steps[1].description == "Step 2"
    assert steps[1].done is False


def test_all_steps_failure(roadmap: SQLiteRoadmapStorage) -> None:
    with pytest.raises(StorageError):
        roadmap._conn.execute("DROP TABLE steps")
        roadmap.all_steps()


def test_mark_done_nonexistent_step(roadmap: SQLiteRoadmapStorage) -> None:
    with pytest.raises(StepNotFoundError):
        roadmap.mark_done("999")  # Assuming this ID does not exist

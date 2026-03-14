"""Unit tests for the TaskStore implementation."""

import sqlite3

import pytest

from smelt.db.schema import init_db
from smelt.db.store import TaskStore
from smelt.exceptions import (
    CircularDependencyError,
    InvalidStatusTransitionError,
    TaskNotFoundError,
)


@pytest.fixture
def store() -> TaskStore:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return TaskStore(conn)


def test_add_and_get_task(store: TaskStore) -> None:
    task = store.add_task("test task", priority=5, complexity=3)
    assert task.description == "test task"
    assert task.priority == 5
    assert task.complexity == 3
    assert task.status == "ready"

    fetched = store.get_task(task.id)
    assert fetched is not None
    assert fetched.id == task.id


def test_get_nonexistent_task(store: TaskStore) -> None:
    assert store.get_task("nonexistent") is None


def test_list_tasks(store: TaskStore) -> None:
    store.add_task("t1", priority=1)
    store.add_task("t2", priority=10)
    store.add_task("t3", priority=5)

    tasks = store.list_tasks()
    assert len(tasks) == 3
    assert [t.description for t in tasks] == ["t2", "t3", "t1"]


def test_list_tasks_filtered(store: TaskStore) -> None:
    store.add_task("ready task")
    t2 = store.add_task("in-progress task")
    store.update_status(t2.id, "in-progress")

    tasks = store.list_tasks(status="in-progress")
    assert len(tasks) == 1
    assert tasks[0].id == t2.id


def test_update_status(store: TaskStore) -> None:
    t1 = store.add_task("t1")
    store.update_status(t1.id, "in-progress")
    t1_updated = store.get_task(t1.id)
    assert t1_updated is not None
    assert t1_updated.status == "in-progress"


def test_update_status_invalid(store: TaskStore) -> None:
    t1 = store.add_task("t1")
    with pytest.raises(InvalidStatusTransitionError, match="Invalid status"):
        store.update_status(t1.id, "unknown-status")


def test_update_status_not_found(store: TaskStore) -> None:
    with pytest.raises(TaskNotFoundError):
        store.update_status("nope", "in-progress")


def test_pick_next_task_no_deps(store: TaskStore) -> None:
    store.add_task("t1", priority=5)
    store.add_task("t2", priority=10)

    next_task = store.pick_next_task()
    assert next_task is not None
    assert next_task.description == "t2"


def test_pick_next_task_with_deps(store: TaskStore) -> None:
    t1 = store.add_task("t1", priority=10)
    t2 = store.add_task("t2", priority=5, depends_on=[t1.id])

    # t1 should be picked because t2 is blocked by t1
    next_task = store.pick_next_task()
    assert next_task is not None
    assert next_task.id == t1.id

    # If t1 is merged, t2 should become executable
    store.update_status(t1.id, "merged")
    next_task2 = store.pick_next_task()
    assert next_task2 is not None
    assert next_task2.id == t2.id


def test_pick_next_task_ignores_non_ready(store: TaskStore) -> None:
    t1 = store.add_task("t1")
    store.update_status(t1.id, "in-progress")
    assert store.pick_next_task() is None


def test_circular_dependency(store: TaskStore) -> None:
    t1 = store.add_task("t1")
    t2 = store.add_task("t2")
    t3 = store.add_task("t3")

    store.add_dependency(t2.id, t1.id)
    store.add_dependency(t3.id, t2.id)

    with pytest.raises(CircularDependencyError, match="creates a cycle"):
        store.add_dependency(t1.id, t3.id)


def test_self_dependency(store: TaskStore) -> None:
    t1 = store.add_task("t1")
    with pytest.raises(CircularDependencyError, match="cannot depend on itself"):
        store.add_dependency(t1.id, t1.id)


def test_add_dependency_missing_task(store: TaskStore) -> None:
    t1 = store.add_task("t1")
    with pytest.raises(TaskNotFoundError, match="Dependency task 'nope' not found"):
        store.add_dependency(t1.id, "nope")

    with pytest.raises(TaskNotFoundError, match="Task 'nope' not found"):
        store.add_dependency("nope", t1.id)


def test_get_dependencies(store: TaskStore) -> None:
    t1 = store.add_task("t1")
    t2 = store.add_task("t2")
    t3 = store.add_task("t3", depends_on=[t1.id, t2.id])

    deps = store.get_dependencies(t3.id)
    assert len(deps) == 2
    assert {d.id for d in deps} == {t1.id, t2.id}


def test_diamond_dependency_visited_branch(store: TaskStore) -> None:
    # Test to hit the `current not in visited` branch returning False
    t1 = store.add_task("t1")
    t2 = store.add_task("t2")
    t3 = store.add_task("t3")
    t4 = store.add_task("t4")
    t5 = store.add_task("t5")
    tx = store.add_task("tx")

    # t4 -> t2, t3 -> t5 -> t1
    store.add_dependency(t5.id, t1.id)
    store.add_dependency(t2.id, t5.id)
    store.add_dependency(t3.id, t5.id)
    store.add_dependency(t4.id, t2.id)
    store.add_dependency(t4.id, t3.id)

    # Adding tx -> t4 will check _path_exists(t4.id, tx.id)
    # BFS will enqueue t5 twice, and hit the 'current already in visited' branch
    store.add_dependency(tx.id, t4.id)

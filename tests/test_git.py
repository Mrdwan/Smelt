"""Unit tests for the GitOps wrapper."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from smelt.config import GitConfig
from smelt.exceptions import GitError
from smelt.git import GitOps


@pytest.fixture
def repo_path(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def config() -> GitConfig:
    return GitConfig(base_branch="main", branch_prefix="smelt/")


@pytest.fixture
def git(repo_path: Path, config: GitConfig) -> GitOps:
    return GitOps(repo_path, config)


def test_successful_run(git: GitOps, mocker: MagicMock) -> None:
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.stdout = "result_output\n"

    result = git._run("status")
    assert result == "result_output"

    # Check that subprocess.run was called correctly
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert args[0] == ["git", "status"]
    assert kwargs["cwd"] == git.repo_path
    assert kwargs["check"] is True


def test_failed_run(git: GitOps, mocker: MagicMock) -> None:
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd=["git", "status"], stderr="fatal: not a git repository\n"
    )

    with pytest.raises(GitError, match="not a git repository"):
        git._run("status")


def test_checkout_branch(git: GitOps, mocker: MagicMock) -> None:
    mock_run = mocker.patch.object(git, "_run")
    git.checkout_branch("my-branch")
    mock_run.assert_called_once_with("checkout", "my-branch")


def test_create_branch(git: GitOps, mocker: MagicMock) -> None:
    mock_run = mocker.patch.object(git, "_run")
    branch_name = git.create_branch("task-123")

    assert branch_name == "smelt/task-123"
    mock_run.assert_called_once_with("checkout", "-b", "smelt/task-123", "main")


def test_pull(git: GitOps, mocker: MagicMock) -> None:
    mock_run = mocker.patch.object(git, "_run")
    git.pull("feature")
    mock_run.assert_called_once_with("pull", "origin", "feature")

    mock_run.reset_mock()
    git.pull()
    mock_run.assert_called_once_with("pull")


def test_add_commit_push(git: GitOps, mocker: MagicMock) -> None:
    mock_run = mocker.patch.object(git, "_run")

    git.add_all()
    mock_run.assert_called_with("add", ".")

    git.commit("test msg")
    mock_run.assert_called_with("commit", "-m", "test msg")

    git.push("smelt/task-123")
    mock_run.assert_called_with("push", "-u", "origin", "smelt/task-123")


def test_current_branch(git: GitOps, mocker: MagicMock) -> None:
    mock_run = mocker.patch.object(git, "_run", return_value="main")
    result = git.current_branch()
    assert result == "main"
    mock_run.assert_called_once_with("branch", "--show-current")


def test_branch_exists(git: GitOps, mocker: MagicMock) -> None:
    # First test True case (success)
    mock_run = mocker.patch.object(git, "_run")
    assert git.branch_exists("my-branch") is True
    mock_run.assert_called_once_with(
        "show-ref", "--verify", "--quiet", "refs/heads/my-branch"
    )

    # Second test False case (raises GitError)
    mock_run.side_effect = GitError("failed")
    assert git.branch_exists("fake-branch") is False


def test_delete_branch(git: GitOps, mocker: MagicMock) -> None:
    mock_run = mocker.patch.object(git, "_run")
    git.delete_branch("my-branch")
    mock_run.assert_called_once_with("branch", "-D", "my-branch")

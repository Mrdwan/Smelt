"""Goose coding agent adapter implementing the CodingAgent protocol.

This is the only file in Smelt that knows about Goose. Every other module
depends on the CodingAgent protocol. To swap Goose for a different agent,
write a new adapter and change one line in cli.py.
"""

from __future__ import annotations

import subprocess
import time
import uuid

from smelt.db.models import AgentResult
from smelt.exceptions import AgentError, AgentTimeoutError

_GOOSE_DEFAULT_EXECUTABLE: str = "goose"


class GooseAdapter:
    """Invokes the Goose CLI headlessly as a subprocess.

    Satisfies the CodingAgent protocol. The pipeline stages receive a
    CodingAgent and never import this class directly.
    """

    def __init__(self, executable: str = _GOOSE_DEFAULT_EXECUTABLE) -> None:
        """Initialize the Goose adapter.

        Args:
            executable: Path or name of the goose CLI executable.
        """
        self._executable = executable

    def run_session(
        self,
        *,
        prompt: str,
        working_dir: str,
        timeout_seconds: int,
        read_only: bool = False,
    ) -> AgentResult:
        """Run a headless Goose session.

        Goose is invoked as a subprocess. The prompt is passed via stdin
        so it does not appear in the process argument list (avoids shell quoting
        issues and keeps sensitive context off the process table).

        Args:
            prompt: The full prompt/instructions for the agent.
            working_dir: The directory the agent should operate in.
            timeout_seconds: Maximum seconds before the session is killed.
            read_only: If True, passes --no-write to Goose (read-only mode).

        Returns:
            AgentResult describing the outcome.

        Raises:
            AgentTimeoutError: If the session exceeds timeout_seconds.
            AgentError: If Goose exits with a non-zero return code.
        """
        session_id = str(uuid.uuid4())[:8]
        start = time.monotonic()

        cmd = [self._executable, "run", "--text", prompt]
        if read_only:
            cmd.append("--no-write")

        try:
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=True,
            )
            duration = time.monotonic() - start
            return AgentResult(
                success=True,
                session_id=session_id,
                output=result.stdout.strip(),
                duration_seconds=duration,
            )
        except subprocess.TimeoutExpired as e:
            raise AgentTimeoutError(
                f"Goose session timed out after {timeout_seconds}s"
            ) from e
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.strip() if e.stderr else e.stdout.strip()
            raise AgentError(
                f"Goose session failed (exit {e.returncode}): {error_output}"
            ) from e

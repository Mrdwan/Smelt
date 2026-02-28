import shutil
import subprocess

from smelt.agents.base import Agent
from smelt.exceptions import AgentNotFoundError


class AiderAgent(Agent):
    def __init__(self, model: str):
        self.model = model

        if not shutil.which("aider"):
            raise AgentNotFoundError("Aider is not installed or not in PATH.")

    def run(self, message: str, context_files: list[str]) -> bool:
        cmd: list[str] = [
            "aider",
            "--model",
            self.model,
            "--message",
            message,
            "--yes-always",
            "--no-auto-commits",
            "--no-stream",
            "--no-suggest-shell-commands",
        ]

        for f in context_files:
            cmd.extend(["--read", f])

        result = subprocess.run(cmd, cwd=".")
        return result.returncode == 0

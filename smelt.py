#!/usr/bin/env python3
"""
Smelt — Raw task in, refined code out.

Usage:
    python smelt.py                  # runs next unchecked step
    python smelt.py "custom task"    # runs a custom task instead

Environment:
    SMELT_MODEL    — model for Aider (default: anthropic/claude-sonnet-4-5-20250929)
    SMELT_PROJECT  — path to your project (default: current directory)
"""

import os
import re
import subprocess
import sys
from pathlib import Path


MODEL = os.environ.get("SMELT_MODEL", "anthropic/claude-sonnet-4-5-20250929")
PROJECT = Path(os.environ.get("SMELT_PROJECT", ".")).resolve()
MEMORY_DIR = PROJECT / "memory"


def find_next_step() -> tuple[str, str, str] | None:
    """Returns (step_id, description, raw_line) or None if all done."""
    roadmap = MEMORY_DIR / "ROADMAP.md"
    if not roadmap.exists():
        print(f"No ROADMAP.md found at {roadmap}")
        sys.exit(1)

    pattern = r'^\s*-\s*\[ \]\s*\*{0,2}Step\s+(\d+\.\d+):?\*{0,2}\s*(.*)'
    for line in roadmap.read_text().splitlines():
        m = re.match(pattern, line)
        if m:
            return m.group(1), m.group(2).strip(), line.strip()
    return None


def mark_step_done(raw_line: str) -> None:
    roadmap = MEMORY_DIR / "ROADMAP.md"
    content = roadmap.read_text()
    roadmap.write_text(content.replace(raw_line, raw_line.replace("- [ ]", "- [x]", 1), 1))


def build_context(task: str) -> str:
    """Build the message Aider receives."""
    parts = []

    for name in ["ARCHITECTURE.md", "DECISIONS.md", "PROGRESS.md"]:
        f = MEMORY_DIR / name
        if f.exists():
            parts.append(f"## {name}\n{f.read_text().strip()}")

    parts.append(f"""## Task

{task}

Figure out what files to create or modify. Write clean code with tests.
- pytest tests in tests/
- Type hints on function signatures
- Specific exceptions, no bare except
- Guard against NaN/division by zero where relevant
""")

    return "\n\n---\n\n".join(parts)


def build_aider_cmd(message: str) -> list[str]:
    """Build the Aider command."""
    cmd = [
        "aider",
        "--model", MODEL,
        "--message", message,
        "--yes-always",
        "--no-auto-commits",
        "--no-stream",
        "--no-suggest-shell-commands",
    ]

    # Add memory files as read-only context
    for name in ["ARCHITECTURE.md", "DECISIONS.md", "PROGRESS.md"]:
        f = MEMORY_DIR / name
        if f.exists():
            cmd.extend(["--read", str(f.relative_to(PROJECT))])

    return cmd


def run_aider(message: str) -> bool:
    """Run Aider and return True if it succeeded."""
    cmd = build_aider_cmd(message)
    print(f"Running: aider --model {MODEL} ...")
    print()

    result = subprocess.run(cmd, cwd=PROJECT)
    return result.returncode == 0


def main():
    # Custom task or next step from roadmap
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        step_id = None
        raw_line = None
        print(f"Custom task: {task[:100]}")
    else:
        step = find_next_step()
        if not step:
            print("All steps complete.")
            return
        step_id, description, raw_line = step
        task = f"Step {step_id}: {description}"
        print(f"Next step: {task}")

    print(f"Model: {MODEL}")
    print(f"Project: {PROJECT}")
    print()

    message = build_context(task)
    success = run_aider(message)

    if success and raw_line:
        answer = input("\nMark step as done in ROADMAP? [y/n] ")
        if answer.strip().lower() == "y":
            mark_step_done(raw_line)
            print(f"Step {step_id} marked done.")

    if not success:
        print("\nAider exited with errors.")
        sys.exit(1)


if __name__ == "__main__":
    main()

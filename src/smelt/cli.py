"""Smelt CLI — command-line interface for the Smelt orchestrator."""

from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from smelt import __version__
from smelt.config import SmeltConfig
from smelt.db.schema import init_db
from smelt.db.store import TaskStore
from smelt.exceptions import SmeltError
from smelt.git import GitOps

console = Console()


def _get_db() -> TaskStore:
    """Get the initialized TaskStore.

    Uses SMELT_DB_PATH env var if set (for tests),
    otherwise defaults to .smelt/roadmap.db in the current directory.
    """
    db_path = os.environ.get("SMELT_DB_PATH")
    if not db_path:
        db_path = ".smelt/roadmap.db"
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return TaskStore(conn)


@click.group()
@click.version_option(version=__version__, prog_name="smelt")
def cli() -> None:
    """Smelt — orchestrate AI coding agents to ship code autonomously."""


def _get_config() -> SmeltConfig:
    """Load SmeltConfig from smelt.toml or return defaults."""
    toml_path = Path("smelt.toml")
    if toml_path.is_file():
        return SmeltConfig.from_toml(toml_path)
    return SmeltConfig.default()


@cli.command()
@click.option("--task", default=None, help="Execute a specific task by ID.")
def run(task: str | None) -> None:
    """Pick the next task and execute the full pipeline."""
    from smelt.agents.goose_adapter import GooseAdapter
    from smelt.agents.llm_client import LiteLLMClient
    from smelt.pipeline.runner import PipelineRunner

    config = _get_config()
    store = _get_db()
    repo_path = Path.cwd()
    git = GitOps(repo_path, config.git)

    specific_task = None
    if task:
        specific_task = store.get_task(task)
        if specific_task is None:
            console.print(f"[bold red]Error:[/] Task '{task}' not found.")
            raise click.Abort()
        console.print(f"[bold cyan]smelt[/] → running task [yellow]{task}[/] …")
    else:
        console.print("[bold cyan]smelt[/] → picking next ready task …")

    runner = PipelineRunner(
        config=config,
        store=store,
        git=git,
        llm=LiteLLMClient(),
        agent=GooseAdapter(),
        repo_path=repo_path,
    )

    result = runner.run(specific_task)

    if result.success:
        console.print(f"[bold green]Pipeline passed![/] {result.message}")
    else:
        console.print(
            f"[bold red]Pipeline failed[/] at [yellow]{result.stage_reached}[/]: "
            f"{result.message}"
        )


@cli.command()
@click.argument("description")
@click.option("--context", default=None, help="External context to attach.")
@click.option("--depends-on", default=None, help="Comma-separated task IDs.")
def add(description: str, context: str | None, depends_on: str | None) -> None:
    """Add a new task to the roadmap."""
    deps = [d.strip() for d in depends_on.split(",")] if depends_on else None

    try:
        store = _get_db()
        task = store.add_task(
            description=description,
            context=context,
            depends_on=deps,
        )
        console.print(
            f"[bold cyan]smelt[/] → added task [yellow]{task.id}[/]: "
            f"[green]{description}[/]"
        )
        if context:
            console.print(f"  context: {context}")
        if depends_on:
            console.print(f"  depends on: {depends_on}")
    except SmeltError as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise click.Abort() from e


@cli.command()
def status() -> None:
    """Show the current task board."""
    store = _get_db()
    tasks = store.list_tasks()

    if not tasks:
        console.print("[bold cyan]smelt[/] → task board is empty")
        return

    table = Table(title="Smelt Task Board")
    table.add_column("ID", style="yellow")
    table.add_column("Status", style="magenta")
    table.add_column("Priority", justify="right")
    table.add_column("Description")

    for task in tasks:
        table.add_row(
            task.id,
            task.status,
            str(task.priority),
            task.description,
        )

    console.print(table)


@cli.command()
@click.option("--check", is_flag=True, help="Check only, do not fix (CI mode).")
def lint(*, check: bool) -> None:
    """Lint and format the codebase with ruff."""
    if check:
        console.print("[bold cyan]smelt[/] → checking lint (CI mode) …")
        try:
            subprocess.run(["ruff", "check", "."], check=True)
            subprocess.run(["ruff", "format", "--check", "."], check=True)
            console.print("[bold green]All checks passed![/]")
        except subprocess.CalledProcessError as e:
            console.print("[bold red]Linting failed.[/]")
            raise click.Abort() from e
    else:
        console.print("[bold cyan]smelt[/] → fixing lint + formatting …")
        try:
            subprocess.run(["ruff", "check", "--fix", "."], check=True)
            subprocess.run(["ruff", "format", "."], check=True)
            console.print("[bold green]Linting and formatting complete![/]")
        except subprocess.CalledProcessError as e:
            console.print("[bold red]Linting failed.[/]")
            raise click.Abort() from e


@cli.command()
def history() -> None:
    """Browse past pipeline runs."""
    console.print("[bold cyan]smelt[/] → run history")
    console.print("[dim]Observability not yet implemented.[/]")


@cli.command()
@click.argument("run_id")
def replay(run_id: str) -> None:
    """Replay a past run's conversation."""
    console.print(f"[bold cyan]smelt[/] → replaying run [yellow]{run_id}[/]")
    console.print("[dim]Replay not yet implemented.[/]")


@cli.command()
def cleanup() -> None:
    """Delete stale failed branches."""
    console.print("[bold cyan]smelt[/] → cleaning up stale branches …")
    console.print("[dim]Cleanup not yet implemented.[/]")


@cli.command()
@click.argument("task_id")
def decompose(task_id: str) -> None:
    """Run the decomposer on an existing task."""
    console.print(f"[bold cyan]smelt[/] → decomposing task [yellow]{task_id}[/]")
    console.print("[dim]Decomposer not yet implemented.[/]")

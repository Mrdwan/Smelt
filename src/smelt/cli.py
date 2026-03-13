"""Smelt CLI — command-line interface for the Smelt orchestrator."""

from __future__ import annotations

import click
from rich.console import Console

from smelt import __version__

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="smelt")
def cli() -> None:
    """Smelt — orchestrate AI coding agents to ship code autonomously."""


@cli.command()
@click.option("--task", default=None, help="Execute a specific task by ID.")
def run(task: str | None) -> None:
    """Pick the next task and execute the full pipeline."""
    if task:
        console.print(f"[bold cyan]smelt[/] → running task [yellow]{task}[/] …")
    else:
        console.print("[bold cyan]smelt[/] → picking next ready task …")
    console.print("[dim]Pipeline not yet implemented.[/]")


@cli.command()
@click.argument("description")
@click.option("--context", default=None, help="External context to attach.")
@click.option("--depends-on", default=None, help="Comma-separated task IDs.")
def add(description: str, context: str | None, depends_on: str | None) -> None:
    """Add a new task to the roadmap."""
    console.print(f"[bold cyan]smelt[/] → adding task: [green]{description}[/]")
    if context:
        console.print(f"  context: {context}")
    if depends_on:
        console.print(f"  depends on: {depends_on}")
    console.print("[dim]Roadmap DB not yet implemented.[/]")


@cli.command()
def status() -> None:
    """Show the current task board."""
    console.print("[bold cyan]smelt[/] → task board")
    console.print("[dim]Roadmap DB not yet implemented.[/]")


@cli.command()
@click.option("--check", is_flag=True, help="Check only, do not fix (CI mode).")
def lint(*, check: bool) -> None:
    """Lint and format the codebase with ruff."""
    if check:
        console.print("[bold cyan]smelt[/] → checking lint (CI mode) …")
    else:
        console.print("[bold cyan]smelt[/] → fixing lint + formatting …")
    console.print("[dim]Lint runner not yet implemented.[/]")


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

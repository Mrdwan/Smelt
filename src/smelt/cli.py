import typer

from smelt.agents.aider import AiderAgent
from smelt.config import settings
from smelt.exceptions import AgentNotFoundError, StorageError
from smelt.roadmap.sqlite import SQLiteRoadmapStorage

app = typer.Typer()


@app.command()
def next() -> None:
    """Print the next roadmap step and optionally run the agent on it."""
    with SQLiteRoadmapStorage(settings.db_path) as roadmap:
        try:
            step = roadmap.next_step()
        except StorageError as e:
            typer.echo(f"Error reading roadmap: {e}", err=True)
            raise typer.Exit(code=1)

        if step is None:
            typer.echo("No steps remaining.")
            return

        typer.echo(f"\nNext step:\n  {step.description}\n")

        if not typer.confirm("Start working on this?"):
            return

        context_files = [
            str(settings.memory / name)
            for name in settings.context_files
            if (settings.memory / name).exists()
        ]

        try:
            agent = AiderAgent(model=settings.model)
        except AgentNotFoundError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=1)

        success = agent.run(message=step.description, context_files=context_files)

        if success:
            try:
                roadmap.mark_done(step.id)
            except StorageError as e:
                typer.echo(
                    f"Agent succeeded but failed to mark step as done: {e}", err=True
                )
                raise typer.Exit(code=1)
            typer.echo("Step completed and marked as done.")
        else:
            typer.echo("Agent failed. Step not marked as done.", err=True)
            raise typer.Exit(code=1)


@app.command()
def add(
    description: str = typer.Argument(..., help="Description of the step to add"),
) -> None:
    """Add a new step to the roadmap."""
    with SQLiteRoadmapStorage(settings.db_path) as roadmap:
        try:
            step_id = roadmap.add_step(description)
        except StorageError as e:
            typer.echo(f"Error adding step: {e}", err=True)
            raise typer.Exit(code=1)

    typer.echo(f"Step added (id={step_id}): {description}")


@app.command()
def done(step_id: str = typer.Argument(..., help="ID of the step to mark as done")) -> None:
    """Manually mark a step as done."""
    with SQLiteRoadmapStorage(settings.db_path) as roadmap:
        try:
            roadmap.mark_done(step_id)
        except StorageError as e:
            typer.echo(f"Error marking step as done: {e}", err=True)
            raise typer.Exit(code=1)

    typer.echo(f"Step {step_id} marked as done.")


@app.command()
def reset(step_id: str = typer.Argument(..., help="ID of the step to reopen")) -> None:
    """Reopen a completed step so it will be picked up by next again."""
    with SQLiteRoadmapStorage(settings.db_path) as roadmap:
        try:
            roadmap.reset_step(step_id)
        except StorageError as e:
            typer.echo(f"Error resetting step: {e}", err=True)
            raise typer.Exit(code=1)

    typer.echo(f"Step {step_id} reopened.")


@app.command()
def status() -> None:
    """Show all roadmap steps and their completion status."""
    with SQLiteRoadmapStorage(settings.db_path) as roadmap:
        try:
            steps = roadmap.all_steps()
        except StorageError as e:
            typer.echo(f"Error reading roadmap: {e}", err=True)
            raise typer.Exit(code=1)

    if not steps:
        typer.echo("No steps in the roadmap.")
        return

    done_count = sum(1 for s in steps if s.done)
    typer.echo(f"\nRoadmap: {done_count}/{len(steps)} done\n")

    for step in steps:
        marker = "[x]" if step.done else "[ ]"
        typer.echo(f"  {marker} {step.description}")

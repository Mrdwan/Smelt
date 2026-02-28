import typer

from smelt.agents.aider import AiderAgent
from smelt.config import settings
from smelt.exceptions import AgentNotFoundError, StorageError
from smelt.roadmap.sqlite import SQLiteRoadmapStorage

app = typer.Typer()


@app.callback()
def main() -> None:
    pass


@app.command()
def next() -> None:
    """Print the next roadmap step and optionally run the agent on it."""
    db_path = settings.memory / settings.roadmap_db
    db_path.parent.mkdir(parents=True, exist_ok=True)

    roadmap = SQLiteRoadmapStorage(str(db_path))

    try:
        step = roadmap.next_step()
    except StorageError as e:
        typer.echo(f"Error reading roadmap: {e}", err=True)
        raise typer.Exit(code=1)

    if step is None:
        typer.echo("No steps remaining.")
        roadmap.close()
        return

    typer.echo(f"\nNext step:\n  {step.description}\n")

    if not typer.confirm("Start working on this?"):
        roadmap.close()
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
        roadmap.close()
        raise typer.Exit(code=1)

    success = agent.run(message=step.description, context_files=context_files)

    if success:
        try:
            roadmap.mark_done(step.id)
        except StorageError as e:
            typer.echo(f"Agent succeeded but failed to mark step as done: {e}", err=True)
            roadmap.close()
            raise typer.Exit(code=1)
        typer.echo("Step completed and marked as done.")
    else:
        typer.echo("Agent failed. Step not marked as done.", err=True)
        roadmap.close()
        raise typer.Exit(code=1)

    roadmap.close()

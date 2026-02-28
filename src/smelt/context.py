from smelt.config import settings


def build_context() -> str:
    """Read project memory files and return the assembled context."""
    parts = []

    for name in settings.context_files:
        f = settings.memory / name
        if f.exists():
            parts.append(f"## {name}\n{f.read_text().strip()}")

    return "\n\n---\n\n".join(parts)

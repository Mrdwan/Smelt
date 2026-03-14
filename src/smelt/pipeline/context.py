"""Repository context builder using tree-sitter for multi-language signature extraction.

Builds a token-budgeted context snapshot of the repository: file tree,
key config files in full, and function/class signatures from all source files.
This is shared across all pipeline stages in a single run.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

from smelt.config import ContextConfig
from smelt.db.models import RepoContext

# Directories to skip when walking the repository
_SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".mypy_cache",
        "__pycache__",
        ".ruff_cache",
        ".pytest_cache",
        "node_modules",
        ".venv",
        "venv",
        ".smelt",
        ".egg-info",
        "dist",
        "build",
        ".tox",
    }
)

# Files to always include in full (key config files)
_CONFIG_FILE_NAMES: frozenset[str] = frozenset(
    {
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "Makefile",
        "Dockerfile",
        "docker-compose.yml",
        "smelt.toml",
        ".gitignore",
        "requirements.txt",
        "package.json",
        "go.mod",
        "Cargo.toml",
    }
)

# File extensions with tree-sitter language support
_SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".go",
        ".rs",
        ".java",
        ".rb",
        ".c",
        ".cpp",
        ".h",
    }
)


class RepoContextBuilder:
    """Builds a token-budgeted repository context snapshot.

    Uses tree-sitter to extract function/class signatures from source files.
    Falls back to a simple regex-style scan when tree-sitter grammars are
    not available for a particular language.
    """

    def __init__(self, *, config: ContextConfig) -> None:
        """Initialize the builder.

        Args:
            config: Context configuration controlling the token budget.
        """
        self._config = config

    def build(self, repo_path: Path) -> RepoContext:
        """Scan the repository and build a context snapshot.

        Args:
            repo_path: Root of the repository to scan.

        Returns:
            RepoContext ready to be rendered into a prompt.
        """
        file_tree = _build_file_tree(repo_path)
        config_files = _read_config_files(repo_path)
        signatures = _extract_signatures(repo_path)
        token_count = (len(file_tree) + len(signatures)) // 4

        return RepoContext(
            file_tree=file_tree,
            signatures=signatures,
            config_files=config_files,
            token_count=token_count,
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_file_tree(repo_path: Path) -> str:
    """Build an indented file tree with file sizes.

    Args:
        repo_path: Repository root.

    Returns:
        Multi-line string with one file/directory per line.
    """
    lines: list[str] = []

    for root, dirs, files in os.walk(repo_path):
        root_path = Path(root)
        # Skip unwanted directories in-place so os.walk won't descend into them
        dirs[:] = sorted(d for d in dirs if d not in _SKIP_DIRS)

        depth = len(root_path.relative_to(repo_path).parts)
        indent = "  " * depth
        folder_name = root_path.name if depth > 0 else str(repo_path)
        lines.append(f"{indent}{folder_name}/")

        file_indent = "  " * (depth + 1)
        for filename in sorted(files):
            file_path = root_path / filename
            try:
                size = file_path.stat().st_size
                size_str = _format_size(size)
            except OSError:  # pragma: no cover
                size_str = "?"
            lines.append(f"{file_indent}{filename} ({size_str})")

    return "\n".join(lines)


def _format_size(size_bytes: int) -> str:
    """Format a file size as a human-readable string.

    Args:
        size_bytes: File size in bytes.

    Returns:
        Human-readable size string (e.g. '1.2 KB').
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _read_config_files(repo_path: Path) -> dict[str, str]:
    """Read key config files from the repository root.

    Only reads files present at the repository root level (not recursively).

    Args:
        repo_path: Repository root.

    Returns:
        Dict mapping filename to file content.
    """
    result: dict[str, str] = {}
    for name in _CONFIG_FILE_NAMES:
        file_path = repo_path / name
        if file_path.is_file():
            with contextlib.suppress(OSError):  # pragma: no cover
                result[name] = file_path.read_text(encoding="utf-8", errors="replace")
    return result


def _extract_signatures(repo_path: Path) -> str:
    """Extract function and class signatures from all source files.

    Attempts tree-sitter parsing first; falls back to simple line scanning
    for languages without an installed grammar.

    Args:
        repo_path: Repository root.

    Returns:
        Multi-line string with one signature per line, prefixed by file path.
    """
    lines: list[str] = []

    for root, dirs, files in os.walk(repo_path):
        root_path = Path(root)
        dirs[:] = sorted(d for d in dirs if d not in _SKIP_DIRS)

        for filename in sorted(files):
            file_path = root_path / filename
            ext = file_path.suffix.lower()
            if ext not in _SUPPORTED_EXTENSIONS:
                continue

            rel_path = file_path.relative_to(repo_path)
            sigs = _extract_from_file(file_path, ext)
            if sigs:
                lines.append(f"\n# {rel_path}")
                lines.extend(sigs)

    return "\n".join(lines)


def _extract_from_file(file_path: Path, ext: str) -> list[str]:
    """Extract signatures from a single source file.

    Tries tree-sitter first, falls back to simple line scanning.

    Args:
        file_path: Absolute path to the source file.
        ext: File extension (e.g. '.py').

    Returns:
        List of signature strings.
    """
    try:
        source = file_path.read_bytes()
    except OSError:  # pragma: no cover
        return []

    # Attempt tree-sitter extraction
    sigs = _try_tree_sitter(source, ext)
    if sigs is not None:
        return sigs

    # Fallback: simple line scan for common patterns
    return _fallback_scan(source)


def _try_tree_sitter(source: bytes, ext: str) -> list[str] | None:
    """Attempt to parse a file with tree-sitter and extract signatures.

    Returns None if tree-sitter is not available for this extension.

    Args:
        source: Raw file bytes.
        ext: File extension.

    Returns:
        List of signatures, or None if tree-sitter is unavailable.
    """
    language_module = _get_tree_sitter_language(ext)
    if language_module is None:
        return None

    try:
        import tree_sitter

        language = tree_sitter.Language(language_module)
        parser = tree_sitter.Parser(language)
        tree = parser.parse(source)
        return _walk_tree_for_signatures(tree.root_node, source)
    except Exception:  # pragma: no cover
        return None


def _get_tree_sitter_language(ext: str) -> object | None:
    """Get the tree-sitter language module for a file extension.

    Returns None if no grammar is installed for this extension.

    Args:
        ext: File extension (e.g. '.py').

    Returns:
        Tree-sitter language object or None.
    """
    try:
        if ext == ".py":
            import tree_sitter_python as _ts_py

            return _ts_py.language()
        if ext in (".js", ".jsx"):  # pragma: no cover
            import tree_sitter_javascript as _ts_js  # type: ignore[import-not-found]

            return _ts_js.language()  # type: ignore[no-any-return]
        if ext in (".ts", ".tsx"):  # pragma: no cover
            import tree_sitter_typescript as _ts_ts  # type: ignore[import-not-found]

            return _ts_ts.language()  # type: ignore[no-any-return]
    except ImportError:  # pragma: no cover
        pass
    return None


def _walk_tree_for_signatures(node: object, source: bytes) -> list[str]:
    """Walk a tree-sitter parse tree and collect definition signatures.

    Extracts class, function, and method definition header lines.

    Args:
        node: Tree-sitter root node.
        source: Original source bytes for text extraction.

    Returns:
        List of signature strings.
    """
    # Import tree-sitter Node type only for isinstance check
    try:
        import tree_sitter
    except ImportError:  # pragma: no cover
        return []

    _DEFINITION_TYPES: frozenset[str] = frozenset(
        {
            "class_definition",
            "function_definition",
            "method_definition",
            "class_declaration",
            "function_declaration",
            "method_declaration",
        }
    )

    sigs: list[str] = []
    stack = [node]

    while stack:
        current = stack.pop()
        if not isinstance(current, tree_sitter.Node):  # pragma: no cover
            continue

        if current.type in _DEFINITION_TYPES:
            # Extract just the first line (the signature, not the body)
            start_byte = current.start_byte
            end_byte = current.end_byte
            text = source[start_byte:end_byte].decode("utf-8", errors="replace")
            first_line = text.split("\n")[0].rstrip()
            if first_line:  # pragma: no branch
                sigs.append(f"  {first_line}")

        stack.extend(reversed(current.children))

    return sigs


def _fallback_scan(source: bytes) -> list[str]:
    """Simple line scan to extract definition-like lines.

    Used when tree-sitter is not available. Looks for common keywords
    that indicate class or function definitions.

    Args:
        source: Raw file bytes.

    Returns:
        List of lines that look like definitions.
    """
    _KEYWORDS: tuple[str, ...] = (
        "def ",
        "class ",
        "async def ",
        "function ",
        "const ",
        "export function ",
        "export class ",
        "export default function ",
        "func ",
        "pub fn ",
        "fn ",
    )

    sigs: list[str] = []
    try:
        text = source.decode("utf-8", errors="replace")
    except Exception:  # pragma: no cover
        return []

    for line in text.splitlines():
        stripped = line.strip()
        if any(stripped.startswith(kw) for kw in _KEYWORDS):
            sigs.append(f"  {stripped}")

    return sigs

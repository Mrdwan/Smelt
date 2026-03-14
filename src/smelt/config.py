"""Configuration loading and validation for Smelt."""

from __future__ import annotations

import tomllib
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from smelt.exceptions import ConfigError


@dataclass(frozen=True)
class ModelsConfig:
    decomposer: str = "claude-opus-4-20250514"
    architect: str = "claude-opus-4-20250514"
    coder: str = "claude-sonnet-4-20250514"
    reviewer: str = "claude-sonnet-4-20250514"
    qc: str = "claude-haiku-4-5-20251001"


@dataclass(frozen=True)
class ContextConfig:
    max_tokens: int = 4000


@dataclass(frozen=True)
class CodingConfig:
    max_retries: int = 3
    timeout_seconds: int = 600


@dataclass(frozen=True)
class ReviewerConfig:
    max_retries: int = 2
    timeout_seconds: int = 300


@dataclass(frozen=True)
class QAConfig:
    run_tests: bool = True
    run_linter: bool = True
    run_type_checker: bool = True
    require_coverage: bool = False
    min_coverage_percent: float = 80.0


@dataclass(frozen=True)
class QCConfig:
    escalation_mode: str = "last_attempt"
    timeout_seconds: int = 300


@dataclass(frozen=True)
class GitConfig:
    base_branch: str = "develop"
    branch_prefix: str = "smelt/"
    lint_before_commit: bool = True


@dataclass(frozen=True)
class InfraConfig:
    retry_delay_seconds: int = 60
    max_infra_retries: int = 3


@dataclass(frozen=True)
class ObservabilityConfig:
    log_dir: str = ".smelt/runs"
    max_runs_retained: int = 50


@dataclass(frozen=True)
class SanityConfig:
    create_bug_ticket_on_failure: bool = True
    bug_ticket_priority: int = 1


@dataclass(frozen=True)
class SmeltConfig:
    """Root configuration object representing smelt.toml."""

    models: ModelsConfig = field(default_factory=ModelsConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    coding: CodingConfig = field(default_factory=CodingConfig)
    reviewer: ReviewerConfig = field(default_factory=ReviewerConfig)
    qa: QAConfig = field(default_factory=QAConfig)
    qc: QCConfig = field(default_factory=QCConfig)
    git: GitConfig = field(default_factory=GitConfig)
    infra: InfraConfig = field(default_factory=InfraConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    sanity: SanityConfig = field(default_factory=SanityConfig)

    @classmethod
    def default(cls) -> SmeltConfig:
        """Return the default configuration."""
        return cls()

    @classmethod
    def from_toml(cls, path: Path) -> SmeltConfig:
        """Load and validate configuration from a TOML file.

        Args:
            path: Path to the smelt.toml file.

        Returns:
            A validated SmeltConfig instance.

        Raises:
            ConfigError: If the file is invalid or missing.
        """
        if not path.is_file():
            raise ConfigError(f"Configuration file not found: {path}")

        try:
            content = path.read_text(encoding="utf-8")
            data = tomllib.loads(content)
        except Exception as e:
            raise ConfigError(f"Failed to parse TOML: {e}") from e

        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> SmeltConfig:
        """Create a config from a dictionary and validate it."""
        KNOWN_SECTIONS = {
            "models",
            "context",
            "coding",
            "reviewer",
            "qa",
            "qc",
            "git",
            "infra",
            "observability",
            "sanity",
        }

        # Warn on unknown root sections
        for key in data:
            if key not in KNOWN_SECTIONS:
                warnings.warn(
                    f"Unknown configuration section in smelt.toml: {key}",
                    stacklevel=2,
                )

        models = ModelsConfig(**data.get("models", {}))
        context = ContextConfig(**data.get("context", {}))
        coding = CodingConfig(**data.get("coding", {}))
        reviewer = ReviewerConfig(**data.get("reviewer", {}))
        qa = QAConfig(**data.get("qa", {}))
        qc_data = data.get("qc", {})
        qc = QCConfig(**qc_data)
        git = GitConfig(**data.get("git", {}))
        infra = InfraConfig(**data.get("infra", {}))
        observability = ObservabilityConfig(**data.get("observability", {}))
        sanity = SanityConfig(**data.get("sanity", {}))

        # Basic validation
        if context.max_tokens <= 0:
            raise ConfigError("context.max_tokens must be positive")
        if coding.max_retries < 0 or reviewer.max_retries < 0:
            raise ConfigError("max_retries cannot be negative")
        if qc.escalation_mode not in ("never", "auto", "last_attempt"):
            raise ConfigError(
                f"Invalid qc.escalation_mode: {qc.escalation_mode}. "
                "Must be 'never', 'auto', or 'last_attempt'."
            )

        return cls(
            models=models,
            context=context,
            coding=coding,
            reviewer=reviewer,
            qa=qa,
            qc=qc,
            git=git,
            infra=infra,
            observability=observability,
            sanity=sanity,
        )

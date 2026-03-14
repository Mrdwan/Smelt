"""Unit tests for the Smelt configuration loading."""

from pathlib import Path

import pytest

from smelt.config import SmeltConfig
from smelt.exceptions import ConfigError


def test_default_config() -> None:
    config = SmeltConfig.default()
    assert config.coding.max_retries == 3
    assert config.git.base_branch == "develop"
    assert config.qc.escalation_mode == "last_attempt"


def test_missing_file() -> None:
    with pytest.raises(ConfigError, match="not found"):
        SmeltConfig.from_toml(Path("does_not_exist_smelt.toml"))


def test_invalid_toml(tmp_path: Path) -> None:
    p = tmp_path / "smelt.toml"
    p.write_text("[bad toml\n")
    with pytest.raises(ConfigError, match="Failed to parse TOML"):
        SmeltConfig.from_toml(p)


def test_valid_custom_toml(tmp_path: Path) -> None:
    p = tmp_path / "smelt.toml"
    p.write_text(
        """
        [coding]
        max_retries = 5

        [git]
        base_branch = "main"

        [qc]
        escalation_mode = "never"
        """
    )
    config = SmeltConfig.from_toml(p)
    assert config.coding.max_retries == 5
    assert config.git.base_branch == "main"
    assert config.qc.escalation_mode == "never"
    # Other values should be defaults
    assert config.reviewer.max_retries == 2


def test_unknown_section_warns(tmp_path: Path) -> None:
    p = tmp_path / "smelt.toml"
    p.write_text(
        """
        [unknown]
        foo = "bar"
        """
    )
    with pytest.warns(UserWarning, match="Unknown configuration section.*unknown"):
        SmeltConfig.from_toml(p)


def test_validation_errors(tmp_path: Path) -> None:
    p = tmp_path / "smelt.toml"

    # Negative tokens
    p.write_text("[context]\nmax_tokens = -1")
    with pytest.raises(ConfigError, match="must be positive"):
        SmeltConfig.from_toml(p)

    # Negative retries
    p.write_text("[coding]\nmax_retries = -5")
    with pytest.raises(ConfigError, match="cannot be negative"):
        SmeltConfig.from_toml(p)

    # Invalid QC mode
    p.write_text("[qc]\nescalation_mode = 'invalid'")
    with pytest.raises(ConfigError, match=r"Invalid qc\.escalation_mode"):
        SmeltConfig.from_toml(p)

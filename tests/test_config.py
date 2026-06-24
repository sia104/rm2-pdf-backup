from pathlib import Path

import pytest

from rm2_backup.config import ConfigError, PlanConfig, load_plan_config, parse_plan_config


def test_parse_plan_config_resolves_relative_metadata_dir() -> None:
    config = parse_plan_config(
        {"plan": {"metadata_dir": "fixtures/synthetic_xochitl"}},
        base_dir=Path("project"),
    )

    assert config == PlanConfig(metadata_dir=Path("project/fixtures/synthetic_xochitl"))


def test_parse_plan_config_requires_plan_table() -> None:
    with pytest.raises(ConfigError, match="plan"):
        parse_plan_config({})


def test_parse_plan_config_requires_metadata_dir() -> None:
    with pytest.raises(ConfigError, match="metadata_dir"):
        parse_plan_config({"plan": {}})


def test_load_plan_config_reads_toml(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()
    config_file.write_text('[plan]\nmetadata_dir = "metadata"\n', encoding="utf-8")

    config = load_plan_config(config_file)

    assert config.metadata_dir == metadata_dir

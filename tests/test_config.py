from pathlib import Path

import pytest

from rm2_backup.config import ConfigError, PlanConfig, load_plan_config, parse_app_config, parse_plan_config


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


def test_parse_app_config_defaults_template_composition_off(tmp_path: Path) -> None:
    config = parse_app_config(_app_payload(tmp_path))

    assert config.renderer.include_templates is False


def test_parse_app_config_reads_template_composition_flag(tmp_path: Path) -> None:
    payload = _app_payload(tmp_path)
    payload["renderer"] = {"mode": "rmc-svg", "include_templates": True}

    config = parse_app_config(payload)

    assert config.renderer.include_templates is True


def test_parse_app_config_rejects_template_composition_for_placeholder(tmp_path: Path) -> None:
    payload = _app_payload(tmp_path)
    payload["renderer"] = {"mode": "placeholder", "include_templates": True}

    with pytest.raises(ConfigError, match="Template composition"):
        parse_app_config(payload)


def _app_payload(tmp_path: Path) -> dict:
    return {
        "rm2": {"host": "rm2"},
        "paths": {
            "backup_root": str(tmp_path / "backup"),
            "raw_current": str(tmp_path / "raw"),
            "pdf_current": str(tmp_path / "pdf"),
            "staging": str(tmp_path / "staging"),
            "database": str(tmp_path / "db.sqlite"),
            "reports": str(tmp_path / "reports"),
            "logs": str(tmp_path / "logs"),
        },
    }

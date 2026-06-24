"""Configuration loading and validation."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """Raised when configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class PlanConfig:
    """Configuration for local metadata-to-PDF-plan dry runs."""

    metadata_dir: Path


@dataclass(frozen=True, slots=True)
class Rm2Config:
    """Connection settings for a reMarkable device."""

    host: str
    user: str = "root"
    ssh_key: Path | None = None
    port: int = 22


@dataclass(frozen=True, slots=True)
class PathsConfig:
    """Filesystem locations used by the backup workflow."""

    backup_root: Path
    raw_current: Path
    pdf_current: Path
    staging: Path
    database: Path
    reports: Path
    logs: Path


@dataclass(frozen=True, slots=True)
class RendererConfig:
    """Renderer configuration.

    ``mode`` is deliberately explicit. ``placeholder`` is suitable only for
    local pipeline tests. ``external`` invokes a configured command template.
    """

    mode: str = "placeholder"
    command: str | None = None


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Full application configuration."""

    rm2: Rm2Config
    paths: PathsConfig
    renderer: RendererConfig


def load_plan_config(path: str | Path) -> PlanConfig:
    """Load a local planning config from TOML."""

    config_path = Path(path)
    payload = _load_toml(config_path)
    return parse_plan_config(payload, base_dir=config_path.parent)


def parse_plan_config(payload: dict[str, Any], *, base_dir: Path | None = None) -> PlanConfig:
    """Parse a local planning config mapping into typed settings."""

    plan = _table(payload, "plan")
    metadata_dir_value = _required_string(plan, "metadata_dir", "plan")
    return PlanConfig(metadata_dir=_resolve_path(metadata_dir_value, base_dir))


def load_app_config(path: str | Path) -> AppConfig:
    """Load a full application config from TOML."""

    config_path = Path(path)
    payload = _load_toml(config_path)
    return parse_app_config(payload, base_dir=config_path.parent)


def parse_app_config(payload: dict[str, Any], *, base_dir: Path | None = None) -> AppConfig:
    """Parse full workflow configuration."""

    rm2_table = _table(payload, "rm2")
    paths_table = _table(payload, "paths")
    renderer_table = payload.get("renderer", {})
    if not isinstance(renderer_table, dict):
        raise ConfigError("Config [renderer] must be a table when present")

    rm2 = Rm2Config(
        host=_required_string(rm2_table, "host", "rm2"),
        user=_optional_string(rm2_table, "user", default="root"),
        ssh_key=_optional_path(rm2_table, "ssh_key", base_dir=base_dir),
        port=_optional_int(rm2_table, "port", default=22),
    )
    paths = PathsConfig(
        backup_root=_required_path(paths_table, "backup_root", base_dir),
        raw_current=_required_path(paths_table, "raw_current", base_dir),
        pdf_current=_required_path(paths_table, "pdf_current", base_dir),
        staging=_required_path(paths_table, "staging", base_dir),
        database=_required_path(paths_table, "database", base_dir),
        reports=_required_path(paths_table, "reports", base_dir),
        logs=_required_path(paths_table, "logs", base_dir),
    )
    renderer = RendererConfig(
        mode=_optional_string(renderer_table, "mode", default="placeholder"),
        command=_optional_string_or_none(renderer_table, "command"),
    )
    _validate_app_config(AppConfig(rm2=rm2, paths=paths, renderer=renderer))
    return AppConfig(rm2=rm2, paths=paths, renderer=renderer)


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Could not read config file: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML config file: {path}") from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"Config root must be a table: {path}")
    return payload


def _table(payload: dict[str, Any], name: str) -> dict[str, Any]:
    value = payload.get(name)
    if not isinstance(value, dict):
        raise ConfigError(f"Config must contain a [{name}] table")
    return value


def _required_string(table: dict[str, Any], key: str, table_name: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or value == "":
        raise ConfigError(f"Config [{table_name}].{key} must be a non-empty string")
    return value


def _optional_string(table: dict[str, Any], key: str, *, default: str) -> str:
    value = table.get(key, default)
    if not isinstance(value, str) or value == "":
        raise ConfigError(f"Config value {key} must be a non-empty string")
    return value


def _optional_string_or_none(table: dict[str, Any], key: str) -> str | None:
    value = table.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or value == "":
        raise ConfigError(f"Config value {key} must be a non-empty string when present")
    return value


def _optional_int(table: dict[str, Any], key: str, *, default: int) -> int:
    value = table.get(key, default)
    if not isinstance(value, int) or value <= 0:
        raise ConfigError(f"Config value {key} must be a positive integer")
    return value


def _required_path(table: dict[str, Any], key: str, base_dir: Path | None) -> Path:
    return _resolve_path(_required_string(table, key, "paths"), base_dir)


def _optional_path(table: dict[str, Any], key: str, *, base_dir: Path | None) -> Path | None:
    value = table.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or value == "":
        raise ConfigError(f"Config value {key} must be a non-empty string when present")
    return _resolve_path(value, base_dir)


def _resolve_path(value: str, base_dir: Path | None) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute() and base_dir is not None:
        path = base_dir / path
    return path


def _validate_app_config(config: AppConfig) -> None:
    allowed_modes = {"placeholder", "external"}
    if config.renderer.mode not in allowed_modes:
        raise ConfigError(f"Renderer mode must be one of {sorted(allowed_modes)}")
    if config.renderer.mode == "external" and config.renderer.command is None:
        raise ConfigError("External renderer mode requires [renderer].command")
    if config.paths.raw_current == config.paths.pdf_current:
        raise ConfigError("raw_current and pdf_current must be different paths")

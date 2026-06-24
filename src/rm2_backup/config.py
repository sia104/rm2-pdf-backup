"""Configuration loading and validation for local dry-run planning."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any


class ConfigError(ValueError):
    """Raised when configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class PlanConfig:
    """Configuration for local metadata-to-PDF-plan dry runs."""

    metadata_dir: Path


def load_plan_config(path: str | Path) -> PlanConfig:
    """Load a local planning config from TOML."""

    config_path = Path(path)
    try:
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Could not read config file: {config_path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML config file: {config_path}") from exc

    return parse_plan_config(payload, base_dir=config_path.parent)


def parse_plan_config(payload: dict[str, Any], *, base_dir: Path | None = None) -> PlanConfig:
    """Parse a local planning config mapping into typed settings."""

    plan = payload.get("plan")
    if not isinstance(plan, dict):
        raise ConfigError("Config must contain a [plan] table")

    metadata_dir_value = plan.get("metadata_dir")
    if not isinstance(metadata_dir_value, str) or metadata_dir_value == "":
        raise ConfigError("Config [plan].metadata_dir must be a non-empty string")

    metadata_dir = Path(metadata_dir_value).expanduser()
    if not metadata_dir.is_absolute() and base_dir is not None:
        metadata_dir = base_dir / metadata_dir

    return PlanConfig(metadata_dir=metadata_dir)

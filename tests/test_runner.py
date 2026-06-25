from pathlib import Path

from rm2_backup.config import AppConfig, PathsConfig, RendererConfig, Rm2Config
from rm2_backup.renderers.external import ExternalCommandRenderer
from rm2_backup.renderers.null import PlaceholderRenderer
from rm2_backup.renderers.rmc_svg import RmcSvgRenderer
from rm2_backup.runner import _renderer_from_config


def _config(tmp_path: Path, mode: str, command: str | None = None) -> AppConfig:
    return AppConfig(
        rm2=Rm2Config(host="rm2"),
        paths=PathsConfig(
            backup_root=tmp_path / "backup",
            raw_current=tmp_path / "backup" / "raw" / "current",
            pdf_current=tmp_path / "backup" / "pdf" / "current",
            staging=tmp_path / "backup" / "staging",
            database=tmp_path / "backup" / "db.sqlite",
            reports=tmp_path / "backup" / "reports",
            logs=tmp_path / "backup" / "logs",
        ),
        renderer=RendererConfig(mode=mode, command=command),
    )


def test_renderer_from_config_uses_placeholder(tmp_path: Path) -> None:
    renderer = _renderer_from_config(_config(tmp_path, "placeholder"))
    assert isinstance(renderer, PlaceholderRenderer)


def test_renderer_from_config_uses_external_command(tmp_path: Path) -> None:
    renderer = _renderer_from_config(_config(tmp_path, "external", "render {uuid} {output}"))
    assert isinstance(renderer, ExternalCommandRenderer)


def test_renderer_from_config_uses_rmc_svg(tmp_path: Path) -> None:
    renderer = _renderer_from_config(_config(tmp_path, "rmc-svg"))
    assert isinstance(renderer, RmcSvgRenderer)

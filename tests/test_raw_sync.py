from pathlib import Path

import pytest

from rm2_backup.config import AppConfig, ConfigError, PathsConfig, RendererConfig, Rm2Config, parse_app_config
from rm2_backup.raw_sync import plan_raw_sync


def test_plan_raw_sync_uses_ssh_alias_without_user_or_port_options(tmp_path: Path) -> None:
    config = _app_config(tmp_path, rm2=Rm2Config(host="rm2", ssh_alias=True))

    commands = plan_raw_sync(config)

    assert commands[0].argv == (
        "rsync",
        "-a",
        "--checksum",
        "--partial",
        "--safe-links",
        "-e",
        "ssh",
        "rm2:/home/root/.local/share/remarkable/xochitl/",
        f"{tmp_path}/raw/xochitl/",
    )
    assert commands[1].argv[7] == "rm2:/usr/share/remarkable/templates/"


def test_plan_raw_sync_uses_explicit_user_port_and_key(tmp_path: Path) -> None:
    key_path = tmp_path / "rm2_key"
    config = _app_config(
        tmp_path,
        rm2=Rm2Config(host="rm2-host", user="root", ssh_key=key_path, port=2222),
    )

    commands = plan_raw_sync(config)

    assert commands[0].argv[6] == "ssh -p 2222 -i " + str(key_path)
    assert commands[0].argv[7] == "root@rm2-host:/home/root/.local/share/remarkable/xochitl/"


def test_parse_app_config_rejects_ssh_alias_with_ssh_key(tmp_path: Path) -> None:
    payload = _app_payload(tmp_path)
    payload["rm2"] = {"host": "rm2", "ssh_alias": True, "ssh_key": "rm2_key"}

    with pytest.raises(ConfigError, match="ssh_alias mode"):
        parse_app_config(payload, base_dir=tmp_path)


def _app_config(tmp_path: Path, *, rm2: Rm2Config) -> AppConfig:
    return AppConfig(
        rm2=rm2,
        paths=PathsConfig(
            backup_root=tmp_path,
            raw_current=tmp_path / "raw",
            pdf_current=tmp_path / "pdf",
            staging=tmp_path / "staging",
            database=tmp_path / "db.sqlite",
            reports=tmp_path / "reports",
            logs=tmp_path / "logs",
        ),
        renderer=RendererConfig(),
    )


def _app_payload(tmp_path: Path) -> dict:
    return {
        "rm2": {"host": "rm2"},
        "paths": {
            "backup_root": str(tmp_path),
            "raw_current": str(tmp_path / "raw"),
            "pdf_current": str(tmp_path / "pdf"),
            "staging": str(tmp_path / "staging"),
            "database": str(tmp_path / "db.sqlite"),
            "reports": str(tmp_path / "reports"),
            "logs": str(tmp_path / "logs"),
        },
    }

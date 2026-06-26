from pathlib import Path


def test_dev_systemd_units_reference_dev_paths() -> None:
    service = Path("deploy/systemd/rm2-backup-dev.service").read_text(encoding="utf-8")
    timer = Path("deploy/systemd/rm2-backup-dev.timer").read_text(encoding="utf-8")

    assert "/home/k11-user/rm2-backup-dev" in service
    assert "/srv/rm2-backup" not in service
    assert "rm2-backup run-local" in service
    assert "rm2-backup-dev.service" in timer


def test_dev_config_example_uses_rmc_svg_renderer() -> None:
    config = Path("deploy/config/dev.example.toml").read_text(encoding="utf-8")

    assert 'mode = "rmc-svg"' in config
    assert '/home/k11-user/rm2-backup-dev' in config
    assert '/srv/rm2-backup' not in config


def test_rpi_dev_systemd_validation_workflow_is_manual_only() -> None:
    workflow = Path(".github/workflows/rpi-dev-systemd-validate.yml").read_text(
        encoding="utf-8"
    )

    assert "workflow_dispatch:" in workflow
    assert "pull_request:" not in workflow
    assert "push:" not in workflow
    assert "runs-on: [self-hosted, rpi, rm2, dev]" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "rm2-backup run-local" in workflow
    assert "rsync " not in workflow
    assert "scp " not in workflow
    assert "ssh " not in workflow

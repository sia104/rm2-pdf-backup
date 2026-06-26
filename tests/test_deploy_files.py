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


def test_production_config_example_uses_placeholders_only() -> None:
    config = Path("deploy/config/production.example.toml").read_text(encoding="utf-8")

    assert "PRODUCTION_RM2_HOST_OR_ALIAS" in config
    assert "192." not in config
    assert "10." not in config
    assert "172." not in config
    assert "ssh_key" not in config
    assert "password" not in config.lower()
    assert "token" not in config.lower()
    assert "/srv/rm2-backup" in config
    assert 'mode = "rmc-svg"' in config


def test_mvp_production_deployment_doc_keeps_manual_gates() -> None:
    doc = Path("docs/mvp-production-deployment.md").read_text(encoding="utf-8")

    assert "Do not run SSH, SCP, or rsync to the RM2 from a developer Mac" in doc
    assert "Stop if any gate fails" in doc
    assert "Do not commit the edited production config" in doc
    assert "must not include `--delete`" in doc
    assert "Production timer is enabled only after" in doc


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
    assert "ExecStart=/bin/true" in workflow
    assert "rsync " not in workflow
    assert "scp " not in workflow
    assert "ssh " not in workflow

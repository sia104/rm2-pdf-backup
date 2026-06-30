from pathlib import Path
import tomllib


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
    assert 'host = "rm2"' in config
    assert "ssh_alias = true" in config
    assert 'user = "root"' not in config
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
    assert "rm2-backup sync-plan --config /etc/rm2-backup/config.toml" in doc
    assert "rm2-backup plan-sync" not in doc
    assert "Production timer is enabled only after" in doc


def test_install_config_run_doc_covers_safe_operator_path() -> None:
    doc = Path("docs/install-config-run.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "docs/README.md" in readme
    assert "docs/install-config-run.md" in readme
    assert "Do not run SSH, SCP, or rsync to the RM2 from a developer Mac" in doc
    assert "rm2-backup --help" in doc
    assert "git clone https://github.com/sia104/rm2-pdf-backup.git" in doc
    assert "sudo mkdir -p /srv/rm2-backup-validation/raw/current" in doc
    assert "sudo mkdir -p /etc/rm2-backup-validation" in doc
    assert "rm2-backup sync-plan --config /etc/rm2-backup-validation/config.toml" in doc
    assert "rm2-backup run-local --config /etc/rm2-backup-validation/config.toml" in doc
    assert "deploy/config/production.example.toml" in doc
    assert "docs/rpi-ssh-access.md" in doc
    assert "docs/mvp-production-deployment.md" in doc
    assert "## Pre-production validation" in doc
    assert "Use a separate validation root and production root." in doc
    assert "It must not include `--delete`" in doc
    assert "Do not commit edited local or production config files" in doc


def test_rmc_extra_declares_renderer_runtime_dependencies() -> None:
    payload = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    rmc_extra = payload["project"]["optional-dependencies"]["rmc"]

    assert "rmc" in rmc_extra
    assert "cairosvg" in rmc_extra
    assert "pypdf" in rmc_extra


def test_rpi_renderer_workflows_use_rmc_extra() -> None:
    workflow_paths = (
        ".github/workflows/rpi-dev-template-render-probe.yml",
        ".github/workflows/rpi-dev-svg-renderer.yml",
        ".github/workflows/rpi-dev-run-local.yml",
        ".github/workflows/rpi-dev-pdf-compose.yml",
        ".github/workflows/rpi-dev-renderer-probe.yml",
        ".github/workflows/rpi-dev-two-run.yml",
        ".github/workflows/rpi-dev-raw-copy.yml",
    )

    for path in workflow_paths:
        workflow = Path(path).read_text(encoding="utf-8")
        assert 'pip install --quiet -e ".[dev,rmc]"' in workflow
        assert "pip install --quiet rmc" not in workflow
        assert "pip install --quiet rmc cairosvg pypdf" not in workflow


def test_install_docs_reference_rmc_extra_for_rpi_runtime() -> None:
    install_doc = Path("docs/install-config-run.md").read_text(encoding="utf-8")
    rpi_doc = Path("docs/development/rpi-install.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert 'pip install -e ".[rmc]"' in install_doc
    assert 'pip install -e ".[dev,rmc]"' in rpi_doc
    assert 'pip install -e ".[rmc]"' in readme


def test_rpi_ssh_access_doc_covers_alias_and_explicit_key_modes() -> None:
    doc = Path("docs/rpi-ssh-access.md").read_text(encoding="utf-8")
    install_doc = Path("docs/install-config-run.md").read_text(encoding="utf-8")
    docs_index = Path("docs/README.md").read_text(encoding="utf-8")

    assert "docs/rpi-ssh-access.md" in install_doc
    assert "rpi-ssh-access.md" in docs_index
    assert "ssh_alias = true" in doc
    assert "rm2:/home/root/.local/share/remarkable/xochitl/" in doc
    assert "Do not use `user = \"\"`" in doc
    assert "ssh_key = \"/PRIVATE/RPI/ONLY/PATH/TO/RM2_KEY\"" in doc
    assert "ssh-keygen -f \"$HOME/.ssh/known_hosts\" -R rm2" in doc
    assert "HostName VALIDATION_RM2_HOST_OR_LOCAL_IP" in doc


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

#!/usr/bin/env python3
"""Rerender selected RM2 notebooks from a temporary raw subset.

This helper is intended for the Raspberry Pi self-hosted runner. It keeps the
normal renderer/validator/publisher path intact while limiting the raw input to
specific notebook UUIDs.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from rm2_backup.config import AppConfig, PathsConfig, load_app_config
from rm2_backup.raw_sync import run_raw_sync
from rm2_backup.runner import run_local


def main() -> int:
    args = _parse_args()
    uuids = _parse_uuid_list(args.notebook_uuids)
    names = _parse_optional_list(args.notebook_names)
    artifact_dir = args.artifact_dir.resolve()
    summary_path = artifact_dir / "selected-rerender-summary.txt"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        f"config_path={args.config}",
        f"source_mode={args.source_mode}",
        f"publish_current={'true' if args.publish_current else 'false'}",
        f"requested_uuid_count={len(uuids)}",
        f"requested_uuids={','.join(uuids)}",
    ]
    if names:
        lines.append(f"requested_names={','.join(names)}")

    try:
        source_config = load_app_config(args.config)
        if args.source_mode == "rm2-live":
            lines.append("raw_sync_attempted=true")
            sync_report = run_raw_sync(source_config)
            lines.append(f"raw_sync_ok={'true' if sync_report.ok else 'false'}")
        else:
            lines.append("raw_sync_attempted=false")

        subset_raw_current = artifact_dir / "runtime" / "raw" / "current"
        subset_raw_current.mkdir(parents=True, exist_ok=True)
        selection = _build_raw_subset(
            source_raw_current=source_config.paths.raw_current,
            subset_raw_current=subset_raw_current,
            uuids=uuids,
        )
        lines.extend(selection.summary_lines)

        temp_config = _selected_run_config(
            source_config,
            artifact_dir=artifact_dir,
            subset_raw_current=subset_raw_current,
            publish_current=args.publish_current,
        )
        result = run_local(temp_config)
        lines.extend(
            [
                f"planned={result.planned}",
                f"completed={result.completed}",
                f"skipped={result.skipped}",
                f"failed={result.failed}",
                f"published={result.published}",
                f"report_path={result.report_path}",
            ]
        )
        _append_pdf_inventory(lines, temp_config.paths.staging, label="staged_pdf")
        _append_pdf_inventory(lines, temp_config.paths.pdf_current, label="published_pdf")
        _copy_report_for_artifact(result.report_path, artifact_dir)

        exit_code = 0 if result.failed == 0 and result.planned == len(uuids) else 1
        if result.planned != len(uuids):
            lines.append("error=planned document count did not match requested uuid count")
    except Exception as exc:  # noqa: BLE001 - runner summary must capture all failures
        lines.append(f"error={type(exc).__name__}: {exc}")
        exit_code = 1

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(summary_path.read_text(encoding="utf-8"))
    return exit_code


class SelectionResult:
    def __init__(self, summary_lines: list[str]) -> None:
        self.summary_lines = summary_lines


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--notebook-uuids", required=True)
    parser.add_argument("--notebook-names", default="")
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument(
        "--source-mode",
        choices=("raw-backup", "rm2-live"),
        default="raw-backup",
    )
    parser.add_argument("--publish-current", action="store_true")
    return parser.parse_args()


def _parse_uuid_list(value: str) -> tuple[str, ...]:
    uuids = tuple(part.strip() for part in value.split(",") if part.strip())
    if not uuids:
        raise ValueError("At least one notebook UUID is required")
    return uuids


def _parse_optional_list(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _build_raw_subset(
    *,
    source_raw_current: Path,
    subset_raw_current: Path,
    uuids: tuple[str, ...],
) -> SelectionResult:
    source_xochitl = source_raw_current / "xochitl"
    source_templates = source_raw_current / "templates"
    subset_xochitl = subset_raw_current / "xochitl"
    subset_templates = subset_raw_current / "templates"
    subset_xochitl.mkdir(parents=True, exist_ok=True)

    if not source_xochitl.is_dir():
        raise FileNotFoundError(f"Missing source xochitl directory: {source_xochitl}")

    metadata_payloads = _load_metadata_payloads(source_xochitl)
    metadata_to_copy: set[str] = set()
    missing: list[str] = []
    for uuid in uuids:
        if uuid not in metadata_payloads:
            missing.append(uuid)
            continue
        metadata_to_copy.update(_metadata_with_ancestors(uuid, metadata_payloads))

    if missing:
        raise FileNotFoundError(f"Requested notebook metadata missing: {','.join(missing)}")

    for uuid in sorted(metadata_to_copy):
        _copy_if_exists(source_xochitl / f"{uuid}.metadata", subset_xochitl / f"{uuid}.metadata")

    copied_document_roots = 0
    copied_top_level_files = 0
    copied_page_candidates = 0
    for uuid in uuids:
        copied_top_level_files += _copy_top_level_uuid_files(source_xochitl, subset_xochitl, uuid)
        copied_document_roots += _copy_document_directory(source_xochitl, subset_xochitl, uuid)
        copied_page_candidates += _copy_page_candidates(source_xochitl, subset_xochitl, uuid)

    if source_templates.is_dir():
        shutil.copytree(source_templates, subset_templates, dirs_exist_ok=True, symlinks=True)
        templates_copied = "true"
    else:
        templates_copied = "false"

    return SelectionResult(
        [
            f"source_raw_current={source_raw_current}",
            f"subset_raw_current={subset_raw_current}",
            f"metadata_copied={len(metadata_to_copy)}",
            f"document_roots_copied={copied_document_roots}",
            f"top_level_document_files_copied={copied_top_level_files}",
            f"page_candidates_copied={copied_page_candidates}",
            f"templates_copied={templates_copied}",
        ]
    )


def _load_metadata_payloads(source_xochitl: Path) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for path in sorted(source_xochitl.glob("*.metadata")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(payload, dict):
            payloads[path.name[: -len(".metadata")]] = payload
    return payloads


def _metadata_with_ancestors(uuid: str, payloads: dict[str, dict[str, Any]]) -> set[str]:
    selected: set[str] = set()
    current = uuid
    while current and current not in selected:
        selected.add(current)
        parent = payloads.get(current, {}).get("parent", "")
        current = parent if isinstance(parent, str) else ""
    return selected


def _copy_top_level_uuid_files(source_xochitl: Path, subset_xochitl: Path, uuid: str) -> int:
    count = 0
    for source in source_xochitl.glob(f"{uuid}.*"):
        if source.is_file():
            _copy_if_exists(source, subset_xochitl / source.name)
            count += 1
    return count


def _copy_document_directory(source_xochitl: Path, subset_xochitl: Path, uuid: str) -> int:
    source_dir = source_xochitl / uuid
    if not source_dir.is_dir():
        return 0
    shutil.copytree(source_dir, subset_xochitl / uuid, dirs_exist_ok=True, symlinks=True)
    return 1


def _copy_page_candidates(source_xochitl: Path, subset_xochitl: Path, uuid: str) -> int:
    content_path = source_xochitl / f"{uuid}.content"
    if not content_path.is_file():
        return 0
    try:
        payload = json.loads(content_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return 0
    pages = payload.get("pages")
    if not isinstance(pages, list):
        return 0

    count = 0
    for page in pages:
        if not isinstance(page, str) or not page:
            continue
        candidates = (
            source_xochitl / f"{page}.rm",
            source_xochitl / f"{uuid}-{page}.rm",
            source_xochitl / uuid / f"{page}.rm",
        )
        for source in candidates:
            if not source.is_file():
                continue
            if source.parent == source_xochitl / uuid:
                destination = subset_xochitl / uuid / source.name
            else:
                destination = subset_xochitl / source.name
            _copy_if_exists(source, destination)
            count += 1
    return count


def _copy_if_exists(source: Path, destination: Path) -> None:
    if not source.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination, follow_symlinks=False)


def _selected_run_config(
    source_config: AppConfig,
    *,
    artifact_dir: Path,
    subset_raw_current: Path,
    publish_current: bool,
) -> AppConfig:
    runtime = artifact_dir / "runtime"
    pdf_current = source_config.paths.pdf_current if publish_current else artifact_dir / "pdf" / "current"
    paths = PathsConfig(
        backup_root=runtime,
        raw_current=subset_raw_current,
        pdf_current=pdf_current,
        staging=artifact_dir / "staging",
        database=artifact_dir / "db" / "selected-rerender.sqlite",
        reports=artifact_dir / "reports",
        logs=artifact_dir / "logs",
    )
    return replace(source_config, paths=paths)


def _append_pdf_inventory(lines: list[str], root: Path, *, label: str) -> None:
    if not root.exists():
        lines.append(f"{label}_root_missing={root}")
        return
    pdfs = sorted(root.rglob("*.pdf"))
    lines.append(f"{label}_count={len(pdfs)}")
    for pdf in pdfs[:50]:
        lines.append(f"{label}={pdf} size={pdf.stat().st_size}")


def _copy_report_for_artifact(report_path: Path | None, artifact_dir: Path) -> None:
    if report_path is None or not report_path.exists():
        return
    destination = artifact_dir / "selected-run-local-report.txt"
    shutil.copy2(report_path, destination)


if __name__ == "__main__":
    sys.exit(main())

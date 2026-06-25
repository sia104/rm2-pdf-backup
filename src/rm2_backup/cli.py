"""Command-line entry point for rm2-pdf-backup."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from rm2_backup.config import ConfigError, PlanConfig, load_app_config, load_plan_config
from rm2_backup.metadata import MetadataParseError, scan_metadata_directory
from rm2_backup.raw_sync import format_sync_plan, plan_raw_sync
from rm2_backup.render_queue import RenderPlanItem, plan_pdf_outputs
from rm2_backup.runner import run_local
from rm2_backup.tree import TreeBuildError, build_visible_tree


def main(argv: Sequence[str] | None = None) -> None:
    """Run the rm2-backup command-line interface."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "plan":
        config = _config_from_args(args)
        plan = _build_plan(config)
        _print_plan(plan)
        return
    if args.command == "sync-plan":
        app_config = _load_app_config_or_exit(args.config)
        print(format_sync_plan(plan_raw_sync(app_config)))
        return
    if args.command == "run-local":
        app_config = _load_app_config_or_exit(args.config)
        result = run_local(app_config)
        print(
            "planned={0.planned} completed={0.completed} skipped={0.skipped} "
            "failed={0.failed} published={0.published} report={0.report_path}".format(result)
        )
        return

    parser.print_help()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rm2-backup",
        description="reMarkable 2 backup and local PDF export workflow",
    )
    subparsers = parser.add_subparsers(dest="command")

    plan_parser = subparsers.add_parser(
        "plan",
        help="dry-run local metadata parsing and PDF output path planning",
    )
    plan_parser.add_argument("--config", type=Path, help="TOML config with [plan].metadata_dir")
    plan_parser.add_argument("--metadata-dir", type=Path, help="local *.metadata directory")

    sync_plan_parser = subparsers.add_parser(
        "sync-plan",
        help="print planned read-only raw sync commands",
    )
    sync_plan_parser.add_argument("--config", type=Path, required=True)

    run_local_parser = subparsers.add_parser(
        "run-local",
        help="run local raw metadata planning and placeholder rendering",
    )
    run_local_parser.add_argument("--config", type=Path, required=True)
    return parser


def _config_from_args(args: argparse.Namespace) -> PlanConfig:
    if args.config is not None and args.metadata_dir is not None:
        raise SystemExit("Use either --config or --metadata-dir, not both")
    if args.config is not None:
        try:
            return load_plan_config(args.config)
        except ConfigError as exc:
            raise SystemExit(str(exc)) from exc
    if args.metadata_dir is not None:
        return PlanConfig(metadata_dir=args.metadata_dir)
    raise SystemExit("plan requires --config or --metadata-dir")


def _load_app_config_or_exit(path: Path):
    try:
        return load_app_config(path)
    except ConfigError as exc:
        raise SystemExit(str(exc)) from exc


def _build_plan(config: PlanConfig) -> tuple[RenderPlanItem, ...]:
    try:
        metadata = scan_metadata_directory(config.metadata_dir)
        tree = build_visible_tree(metadata)
        return plan_pdf_outputs(tree)
    except (MetadataParseError, TreeBuildError) as exc:
        raise SystemExit(str(exc)) from exc


def _print_plan(plan: tuple[RenderPlanItem, ...]) -> None:
    if not plan:
        print("No documents planned for rendering.")
        return

    print("Planned PDF outputs:")
    for item in plan:
        print(f"{item.uuid}\t{item.output_relative_path}")

from pathlib import Path, PurePosixPath

import pytest

from rm2_backup.metadata import MetadataRecord, scan_metadata_directory
from rm2_backup.render_queue import OutputPlanError, build_output_plan
from rm2_backup.tree import build_visible_tree, sanitise_path_segment

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "synthetic_xochitl"


def test_build_output_plan_includes_documents_only() -> None:
    tree = build_visible_tree(scan_metadata_directory(FIXTURE_DIR))
    plan = build_output_plan(tree)

    by_uuid = {item.uuid: item for item in plan}

    assert set(by_uuid) == {
        "doc-duplicate-name",
        "doc-in-folder",
        "doc-root",
        "unknown-type",
    }
    assert "folder-root" not in by_uuid
    assert "folder-sub" not in by_uuid


def test_build_output_plan_preserves_safe_folder_structure() -> None:
    tree = build_visible_tree(scan_metadata_directory(FIXTURE_DIR))
    plan = {item.uuid: item for item in build_output_plan(tree)}

    assert plan["doc-root"].safe_relative_path == PurePosixPath("Root notebook.pdf")
    assert plan["doc-in-folder"].safe_relative_path == PurePosixPath(
        "Backup Test/Notebook in folder.pdf"
    )
    assert plan["doc-duplicate-name"].safe_relative_path == PurePosixPath(
        "Backup Test/Nested Folder/Root notebook.pdf"
    )


def test_build_output_plan_keeps_visible_path_for_reporting() -> None:
    tree = build_visible_tree(scan_metadata_directory(FIXTURE_DIR))
    plan = {item.uuid: item for item in build_output_plan(tree)}

    assert plan["doc-in-folder"].visible_path == ("Backup Test", "Notebook in folder")


def test_output_plan_uses_disambiguated_safe_names() -> None:
    first = _record("first000", "Same", parent="")
    second = _record("second00", "Same", parent="")
    tree = build_visible_tree((first, second))

    plan = {item.uuid: item for item in build_output_plan(tree)}

    assert plan["first000"].safe_relative_path == PurePosixPath("Same [first000].pdf")
    assert plan["second00"].safe_relative_path == PurePosixPath("Same [second00].pdf")


def test_output_plan_detects_path_collisions() -> None:
    first = _record("first", "A/B", parent="")
    second = _record("second", "A:B", parent="")
    tree = build_visible_tree((first, second))

    with pytest.raises(OutputPlanError, match="collision"):
        build_output_plan(tree)


def test_sanitised_segments_do_not_contain_path_separators() -> None:
    assert "/" not in sanitise_path_segment("a/b")
    assert "\\" not in sanitise_path_segment("a\\b")


def _record(uuid: str, visible_name: str, *, parent: str) -> MetadataRecord:
    from rm2_backup.metadata import MetadataKind

    return MetadataRecord(
        uuid=uuid,
        visible_name=visible_name,
        raw_type="DocumentType",
        kind=MetadataKind.DOCUMENT,
        parent=parent,
        deleted=False,
        last_modified=None,
        source_path=Path(f"{uuid}.metadata"),
    )

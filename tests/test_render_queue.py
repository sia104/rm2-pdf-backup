from pathlib import Path, PurePosixPath

from rm2_backup.metadata import scan_metadata_directory
from rm2_backup.render_queue import plan_pdf_outputs
from rm2_backup.tree import build_visible_tree

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "synthetic_xochitl"


def test_plan_pdf_outputs_includes_documents_only() -> None:
    tree = build_visible_tree(scan_metadata_directory(FIXTURE_DIR))
    plan = plan_pdf_outputs(tree)

    assert {item.uuid for item in plan} == {
        "doc-duplicate-name",
        "doc-in-folder",
        "doc-root",
        "unknown-type",
    }
    assert "folder-root" not in {item.uuid for item in plan}


def test_plan_pdf_outputs_preserves_visible_paths() -> None:
    tree = build_visible_tree(scan_metadata_directory(FIXTURE_DIR))
    plan = {item.uuid: item for item in plan_pdf_outputs(tree)}

    assert plan["doc-root"].visible_path == ("Root notebook",)
    assert plan["doc-in-folder"].visible_path == (
        "Backup Test",
        "Notebook in folder",
    )


def test_plan_pdf_outputs_uses_safe_relative_pdf_paths() -> None:
    tree = build_visible_tree(scan_metadata_directory(FIXTURE_DIR))
    plan = {item.uuid: item for item in plan_pdf_outputs(tree)}

    assert plan["doc-root"].output_relative_path == PurePosixPath("Root notebook.pdf")
    assert plan["doc-in-folder"].output_relative_path == PurePosixPath(
        "Backup Test/Notebook in folder.pdf"
    )
    assert plan["doc-duplicate-name"].output_relative_path == PurePosixPath(
        "Backup Test/Nested Folder/Root notebook.pdf"
    )


def test_plan_pdf_outputs_are_deterministic() -> None:
    tree = build_visible_tree(scan_metadata_directory(FIXTURE_DIR))
    first = plan_pdf_outputs(tree)
    second = plan_pdf_outputs(dict(reversed(tuple(tree.items()))))

    assert tuple(item.uuid for item in first) == tuple(item.uuid for item in second)
    assert tuple(item.output_relative_path for item in first) == tuple(
        item.output_relative_path for item in second
    )

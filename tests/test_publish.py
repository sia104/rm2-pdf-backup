from pathlib import PurePosixPath

import pytest

from rm2_backup.metadata import MetadataKind
from rm2_backup.publish import PublishPlanError, plan_pdf_mirror_paths
from rm2_backup.tree import VisibleNode


def test_plan_pdf_mirror_paths_includes_documents_only() -> None:
    tree = {
        "folder": _node(
            uuid="folder",
            kind=MetadataKind.COLLECTION,
            visible_path=("Folder",),
            safe_path=("Folder",),
        ),
        "doc": _node(
            uuid="doc",
            kind=MetadataKind.DOCUMENT,
            visible_path=("Folder", "Notebook"),
            safe_path=("Folder", "Notebook"),
        ),
    }

    plans = plan_pdf_mirror_paths(tree)

    assert len(plans) == 1
    assert plans[0].uuid == "doc"
    assert plans[0].visible_path == ("Folder", "Notebook")
    assert plans[0].relative_pdf_path == PurePosixPath("Folder/Notebook.pdf")


def test_plan_pdf_mirror_paths_keeps_existing_pdf_suffix() -> None:
    tree = {
        "pdfdoc": _node(
            uuid="pdfdoc",
            kind=MetadataKind.DOCUMENT,
            visible_path=("Imported PDF",),
            safe_path=("Imported PDF.pdf",),
        ),
    }

    plans = plan_pdf_mirror_paths(tree)

    assert plans[0].relative_pdf_path == PurePosixPath("Imported PDF.pdf")


def test_plan_pdf_mirror_paths_are_deterministically_sorted() -> None:
    tree = {
        "b": _node(
            uuid="b",
            kind=MetadataKind.DOCUMENT,
            visible_path=("B",),
            safe_path=("B",),
        ),
        "a": _node(
            uuid="a",
            kind=MetadataKind.DOCUMENT,
            visible_path=("A",),
            safe_path=("A",),
        ),
    }

    plans = plan_pdf_mirror_paths(tree)

    assert [plan.uuid for plan in plans] == ["a", "b"]


def test_plan_pdf_mirror_paths_detects_collisions() -> None:
    tree = {
        "one": _node(
            uuid="one",
            kind=MetadataKind.DOCUMENT,
            visible_path=("Report",),
            safe_path=("Report",),
        ),
        "two": _node(
            uuid="two",
            kind=MetadataKind.DOCUMENT,
            visible_path=("Report.pdf",),
            safe_path=("Report.pdf",),
        ),
    }

    with pytest.raises(PublishPlanError, match="collision"):
        plan_pdf_mirror_paths(tree)


def _node(
    *,
    uuid: str,
    kind: MetadataKind,
    visible_path: tuple[str, ...],
    safe_path: tuple[str, ...],
) -> VisibleNode:
    return VisibleNode(
        uuid=uuid,
        visible_name=visible_path[-1],
        safe_name=safe_path[-1],
        kind=kind,
        parent="",
        visible_path=visible_path,
        safe_path=safe_path,
    )

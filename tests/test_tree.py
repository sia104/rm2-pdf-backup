from pathlib import Path

import pytest

from rm2_backup.metadata import MetadataRecord, scan_metadata_directory
from rm2_backup.tree import TreeBuildError, build_visible_tree, sanitise_path_segment

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "synthetic_xochitl"


def test_build_visible_tree_resolves_root_and_nested_paths() -> None:
    records = scan_metadata_directory(FIXTURE_DIR)
    tree = build_visible_tree(records)

    assert tree["folder-root"].visible_path == ("Backup Test",)
    assert tree["folder-sub"].visible_path == ("Backup Test", "Nested Folder")
    assert tree["doc-root"].visible_path == ("Root notebook",)
    assert tree["doc-in-folder"].visible_path == ("Backup Test", "Notebook in folder")
    assert tree["doc-duplicate-name"].visible_path == (
        "Backup Test",
        "Nested Folder",
        "Root notebook",
    )


def test_build_visible_tree_excludes_inactive_and_trash_records() -> None:
    records = scan_metadata_directory(FIXTURE_DIR)
    tree = build_visible_tree(records)

    assert "doc-trash" not in tree
    assert "doc-deleted" not in tree


def test_build_visible_tree_preserves_kind_helpers() -> None:
    records = scan_metadata_directory(FIXTURE_DIR)
    tree = build_visible_tree(records)

    assert tree["folder-root"].is_collection
    assert not tree["folder-root"].is_document
    assert tree["doc-root"].is_document
    assert not tree["doc-root"].is_collection


def test_sanitise_path_segment_replaces_unsafe_characters() -> None:
    assert sanitise_path_segment('bad/name:with*chars?') == "bad_name_with_chars_"
    assert sanitise_path_segment("  many   spaces  ") == "many spaces"
    assert sanitise_path_segment("...") == "untitled"


def test_duplicate_visible_names_under_same_parent_are_disambiguated() -> None:
    first = _record("first", "Same", parent="")
    second = _record("second", "Same", parent="")

    tree = build_visible_tree((first, second))

    assert tree["first"].safe_path == ("Same [first]",)
    assert tree["second"].safe_path == ("Same [second]",)


def test_duplicate_visible_names_in_different_parents_are_not_disambiguated() -> None:
    folder = _record("folder", "Folder", kind="CollectionType", parent="")
    root_doc = _record("rootdoc", "Same", parent="")
    nested_doc = _record("nestdoc", "Same", parent="folder")

    tree = build_visible_tree((folder, root_doc, nested_doc))

    assert tree["rootdoc"].safe_path == ("Same",)
    assert tree["nestdoc"].safe_path == ("Folder", "Same")


def test_missing_parent_fails_clearly() -> None:
    record = _record("orphan", "Orphan", parent="missing")

    with pytest.raises(TreeBuildError, match="Missing parent"):
        build_visible_tree((record,))


def test_parent_cycle_fails_clearly() -> None:
    first = _record("first", "First", kind="CollectionType", parent="second")
    second = _record("second", "Second", kind="CollectionType", parent="first")

    with pytest.raises(TreeBuildError, match="cycle"):
        build_visible_tree((first, second))


def _record(
    uuid: str,
    visible_name: str,
    *,
    kind: str = "DocumentType",
    parent: str,
) -> MetadataRecord:
    from rm2_backup.metadata import MetadataKind

    if kind == "CollectionType":
        metadata_kind = MetadataKind.COLLECTION
    elif kind == "DocumentType":
        metadata_kind = MetadataKind.DOCUMENT
    else:
        metadata_kind = MetadataKind.UNKNOWN

    return MetadataRecord(
        uuid=uuid,
        visible_name=visible_name,
        raw_type=kind,
        kind=metadata_kind,
        parent=parent,
        deleted=False,
        last_modified=None,
        source_path=Path(f"{uuid}.metadata"),
    )

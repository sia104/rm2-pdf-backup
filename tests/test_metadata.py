from pathlib import Path

import pytest

from rm2_backup.metadata import (
    MetadataKind,
    MetadataParseError,
    parse_metadata_file,
    scan_metadata_directory,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "synthetic_xochitl"


def test_parse_single_metadata_file() -> None:
    record = parse_metadata_file(FIXTURE_DIR / "doc-in-folder.metadata")

    assert record.uuid == "doc-in-folder"
    assert record.visible_name == "Notebook in folder"
    assert record.raw_type == "DocumentType"
    assert record.kind is MetadataKind.DOCUMENT
    assert record.is_document
    assert not record.is_collection
    assert record.parent == "folder-root"
    assert not record.deleted
    assert not record.is_deleted_or_trashed
    assert record.last_modified == "1700000002000"


def test_scan_metadata_directory_reads_all_synthetic_records() -> None:
    records = scan_metadata_directory(FIXTURE_DIR)
    by_uuid = {record.uuid: record for record in records}

    assert set(by_uuid) == {
        "doc-deleted",
        "doc-duplicate-name",
        "doc-in-folder",
        "doc-root",
        "doc-trash",
        "folder-root",
        "folder-sub",
        "unknown-type",
    }
    assert by_uuid["folder-root"].kind is MetadataKind.COLLECTION
    assert by_uuid["folder-root"].is_collection
    assert by_uuid["folder-root"].parent == ""
    assert by_uuid["folder-sub"].parent == "folder-root"
    assert by_uuid["doc-root"].parent == ""


def test_deleted_and_trashed_items_are_detected() -> None:
    records = {record.uuid: record for record in scan_metadata_directory(FIXTURE_DIR)}

    assert records["doc-trash"].is_in_trash
    assert records["doc-trash"].is_deleted_or_trashed
    assert records["doc-deleted"].deleted
    assert records["doc-deleted"].is_deleted_or_trashed


def test_unknown_item_type_is_reported_without_crashing() -> None:
    record = parse_metadata_file(FIXTURE_DIR / "unknown-type.metadata")

    assert record.raw_type == "MysteryType"
    assert record.kind is MetadataKind.UNKNOWN
    assert not record.is_document
    assert not record.is_collection


def test_duplicate_visible_names_can_be_parsed() -> None:
    records = scan_metadata_directory(FIXTURE_DIR)
    duplicate_name_records = [
        record for record in records if record.visible_name == "Root notebook"
    ]

    assert {record.uuid for record in duplicate_name_records} == {
        "doc-root",
        "doc-duplicate-name",
    }


def test_missing_required_field_fails_clearly(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.metadata"
    bad_file.write_text('{"type": "DocumentType"}', encoding="utf-8")

    with pytest.raises(MetadataParseError, match="visibleName"):
        parse_metadata_file(bad_file)


def test_invalid_json_fails_clearly(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.metadata"
    bad_file.write_text("not json", encoding="utf-8")

    with pytest.raises(MetadataParseError, match="Invalid JSON"):
        parse_metadata_file(bad_file)


def test_non_metadata_suffix_fails_clearly(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(
        '{"visibleName": "Bad", "type": "DocumentType"}',
        encoding="utf-8",
    )

    with pytest.raises(MetadataParseError, match=".metadata"):
        parse_metadata_file(bad_file)

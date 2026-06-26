from pathlib import Path

from rm2_backup.renderers.rmc_svg_template import add_template_backgrounds


def test_add_template_backgrounds_returns_original_when_no_template(tmp_path: Path) -> None:
    raw = tmp_path / "raw" / "xochitl"
    raw.mkdir(parents=True)
    svg = tmp_path / "page.svg"
    svg.write_text("", encoding="utf-8")

    result = add_template_backgrounds(
        raw_xochitl=raw,
        uuid="doc",
        svg_paths=(svg,),
        work_dir=tmp_path / "work",
    )

    assert result == (svg,)

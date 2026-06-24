from pathlib import PurePosixPath

from rm2_backup.tree import VisibleNode


class PublishPlanError(ValueError): ...


class PdfMirrorPlan:
    uuid: str
    visible_path: tuple[str, ...]
    relative_pdf_path: PurePosixPath

    def __init__(
        self,
        *,
        uuid: str,
        visible_path: tuple[str, ...],
        relative_pdf_path: PurePosixPath,
    ) -> None: ...


def plan_pdf_mirror_paths(tree: dict[str, VisibleNode]) -> tuple[PdfMirrorPlan, ...]: ...

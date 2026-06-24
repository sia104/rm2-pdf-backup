"""Run orchestration types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Summary of a run."""

    planned: int
    completed: int
    skipped: int
    failed: int

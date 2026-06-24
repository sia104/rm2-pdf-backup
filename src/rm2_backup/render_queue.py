"""Render-queue planning boundaries.

Planned responsibilities:
- decide which documents need rendering;
- keep rendering independent from raw sync and metadata parsing;
- allow failed documents to be retried without blocking unrelated documents.
"""

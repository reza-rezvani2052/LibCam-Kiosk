"""Validate locally supplied model files for LibCam Kiosk.

This module deliberately performs no network access and never downloads weights.
"""

from __future__ import annotations

from pathlib import Path

MINIMUM_MODEL_BYTES = 1_000_000


def is_model_file_valid(model_path: Path) -> bool:
    """Return whether a local model file exists and is not an LFS pointer/incomplete file."""
    path = Path(model_path)
    try:
        return path.is_file() and path.stat().st_size >= MINIMUM_MODEL_BYTES
    except OSError:
        return False

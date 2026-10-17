"""Validate locally supplied model files for LibCam Kiosk.

This module performs local file checks only. It never accesses the network.
"""

from __future__ import annotations

from pathlib import Path

GIT_LFS_POINTER_HEADER = b"version https://git-lfs.github.com/spec/v1"


def is_model_file_available(model_path: Path) -> bool:
    """Reject missing, empty, and unresolved Git LFS pointer files."""
    path = Path(model_path)
    try:
        if not path.is_file() or path.stat().st_size == 0:
            return False
        with path.open("rb") as model_file:
            header = model_file.readline(128).strip()
        return header != GIT_LFS_POINTER_HEADER
    except OSError:
        return False

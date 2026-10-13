"""Runtime paths for the standalone kiosk application."""

from __future__ import annotations

import sys
from pathlib import Path


def application_root() -> Path:
    """Return the project root for source runs or the bundle root when frozen."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def yolo_model_directory() -> Path:
    return application_root() / "models" / "yolo"


def face_model_path() -> Path:
    return yolo_model_directory() / "yolov8n-face-lindevs.pt"


def pose_model_path() -> Path:
    return yolo_model_directory() / "yolo26n-pose.pt"

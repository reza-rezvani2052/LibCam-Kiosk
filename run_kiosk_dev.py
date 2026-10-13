"""Prepare Qt resources and model assets before launching the Kiosk in development mode."""

from __future__ import annotations

import subprocess
import sys

from app.components.member_photo_kiosk.model_assets import (
    MINIMUM_MODEL_BYTES,
    ensure_pose_model,
    )
from app.components.member_photo_kiosk.paths import face_model_path, pose_model_path


def run() -> int:
    try:
        from tools.build import build_qml_resources

        # build_qml_resources.convert_qrc_file_to_python(force=True)
        build_qml_resources.convert_qrc_file_to_python()
        face_path = face_model_path()
        if not face_path.is_file() or face_path.stat().st_size < MINIMUM_MODEL_BYTES:
            raise RuntimeError(
                    "The face-detection weights are missing or are Git LFS pointer files. "
                    "Install Git LFS and run 'git lfs pull' in the repository."
                    )
        ensure_pose_model(pose_model_path())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"LibCam Kiosk preparation failed:\n{exc}", file=sys.stderr)
        return 1

    from kiosk_main import main

    # Development mode allows virtual webcams such as ManyCam.
    return main(allow_virtual_cameras=True)


if __name__ == "__main__":
    raise SystemExit(run())

"""Prepare Qt resources and validate local model files before launching Kiosk."""

from __future__ import annotations

import subprocess
import sys

from app.components.member_photo_kiosk.model_assets import is_model_file_valid
from app.components.member_photo_kiosk.paths import face_model_path, pose_model_path


def run() -> int:
    try:
        model_paths = (face_model_path(), pose_model_path())
        invalid_paths = [path for path in model_paths if not is_model_file_valid(path)]
        if invalid_paths:
            paths = "\n".join(str(path) for path in invalid_paths)
            raise FileNotFoundError(
                "Required model file(s) are missing or incomplete:\n"
                f"{paths}\n"
                "Place both model files in the repository's models/yolo directory. "
                "The development launcher does not download model files."
            )

        from tools.build import build_qml_resources

        # build_qml_resources.convert_qrc_file_to_python(force=True)
        build_qml_resources.convert_qrc_file_to_python()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"LibCam Kiosk preparation failed:\n{exc}", file=sys.stderr)
        return 1

    from kiosk_main import main

    # Development mode allows virtual webcams such as ManyCam.
    return main(allow_virtual_cameras=True)


if __name__ == "__main__":
    raise SystemExit(run())

"""Build the standalone QML LibCam Kiosk bundle."""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.components.member_photo_kiosk.model_assets import (  # noqa: E402
    MINIMUM_MODEL_BYTES,
    ensure_pose_model,
)
from app.components.member_photo_kiosk.paths import face_model_path, pose_model_path  # noqa: E402
from tools.build.build_qml_resources import convert_qrc_file_to_python  # noqa: E402


def check_face_model() -> None:
    model_path = face_model_path()
    if not model_path.is_file() or model_path.stat().st_size < MINIMUM_MODEL_BYTES:
        raise FileNotFoundError(
            "Face-detection model is missing or incomplete: "
            f"{model_path}\nInstall Git LFS and run 'git lfs pull'."
        )


def copy_runtime_models(bundle_directory: Path) -> Path:
    """Copy model weights beside the executable, outside PyInstaller's _internal directory."""
    sources = (face_model_path(), pose_model_path())
    for source in sources:
        if not source.is_file() or source.stat().st_size < MINIMUM_MODEL_BYTES:
            raise FileNotFoundError(
                f"Required model is missing or incomplete: {source}"
            )

    destination = Path(bundle_directory) / "models" / "yolo"
    destination.mkdir(parents=True, exist_ok=True)
    for source in sources:
        shutil.copy2(source, destination / source.name)
    return destination


def _format_elapsed_time(elapsed_seconds: float) -> str:
    """Format elapsed seconds as HH:MM:SS."""
    total_seconds = max(0, int(elapsed_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def main() -> int:
    started_at = time.perf_counter()
    try:
        try:
            check_face_model()
            ensure_pose_model(pose_model_path())
            convert_qrc_file_to_python(force=True)
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "PyInstaller",
                    "--clean",
                    "--noconfirm",
                    f"--workpath={ROOT / 'build' / 'kiosk'}",
                    f"--distpath={ROOT / 'dist' / 'kiosk'}",
                    str(ROOT / "LibCamKiosk.spec"),
                ],
                cwd=ROOT,
                check=True,
            )
        except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
            print(f"Kiosk build failed: {exc}", file=sys.stderr)
            return 1

        executable = ROOT / "dist" / "kiosk" / "LibCamKiosk" / "LibCamKiosk.exe"
        if not executable.is_file():
            print(f"Kiosk executable was not created: {executable}", file=sys.stderr)
            return 1

        try:
            model_directory = copy_runtime_models(executable.parent)
        except OSError as exc:
            print(f"Kiosk model deployment failed: {exc}", file=sys.stderr)
            return 1

        print(f"Model files copied to: {model_directory}")
        print(f"LibCam Kiosk build succeeded: {executable}")
        return 0
    finally:
        elapsed = time.perf_counter() - started_at
        print(f"Build duration: {_format_elapsed_time(elapsed)}")


if __name__ == "__main__":
    raise SystemExit(main())

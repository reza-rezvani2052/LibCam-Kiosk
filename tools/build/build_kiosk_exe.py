"""Build the standalone QML LibCam Kiosk bundle."""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DIR_BUILD = ROOT / "build"
DIR_DIST = ROOT / "dist"
MODELS_DIR = ROOT / "models"

from app.components.member_photo_kiosk.model_assets import is_model_file_available
from app.components.member_photo_kiosk.paths import face_model_path, pose_model_path
from tools.build.build_qml_resources import convert_qrc_file_to_python


def remove(path: Path) -> None:
    if not path.exists():
        return

    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def clean() -> None:
    print("Cleaning previous build...")
    # ...
    remove(DIR_BUILD)
    remove(DIR_DIST)
    # فایل *.spec فایل build دائمی پروژه است و نباید هنگام clean حذف شود


def get_version(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def show_versions() -> None:
    # print(f"App Version : {APP_VERSION}")
    print(f"Python      : {sys.version.split()[0]}")
    print(
            "PyInstaller : "
            f"{get_version([sys.executable, '-m', 'PyInstaller', '--version'])}"
            )


def check_model_files() -> None:
    """Fail fast unless both required model files are present locally."""
    model_paths = (face_model_path(), pose_model_path())
    invalid_paths = [path for path in model_paths if not is_model_file_available(path)]
    if invalid_paths:
        paths = "\n".join(str(path) for path in invalid_paths)
        raise FileNotFoundError(
                "Required model file(s) are missing, empty, or unresolved Git LFS pointers:\n"
                f"{paths}\n"
                "Place both model files in the repository's models/yolo directory. "
                "The build does not download model files."
                )


def copy_runtime_models(bundle_directory: Path) -> Path:
    """Copy model weights beside the executable, outside PyInstaller's _internal directory."""
    sources = (face_model_path(), pose_model_path())
    for source in sources:
        if not is_model_file_available(source):
            raise FileNotFoundError(
                    f"Required model is missing, empty, or an unresolved Git LFS pointer: {source}"
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
            show_versions()

            print()
            clean()
            print()

            check_model_files()
            convert_qrc_file_to_python(force=True)
            subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "PyInstaller",
                        "--clean",
                        "--noconfirm",
                        f"--workpath={DIR_BUILD}",
                        f"--distpath={DIR_DIST}",
                        str(ROOT / "LibCam-Kiosk.spec"),
                        ],
                    cwd=ROOT,
                    check=True,
                    )
        except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
            print(f"Kiosk build failed: {exc}", file=sys.stderr)
            return 1

        executable = ROOT / "dist" / "LibCam-Kiosk" / "LibCam-Kiosk.exe"
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

    except KeyboardInterrupt:
        print("\nBuild cancelled by user.")
        sys.exit(2)

    finally:
        elapsed = time.perf_counter() - started_at
        print(f"Build duration: {_format_elapsed_time(elapsed)}")


if __name__ == "__main__":
    raise SystemExit(main())

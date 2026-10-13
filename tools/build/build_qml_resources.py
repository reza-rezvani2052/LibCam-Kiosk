"""Compile Qt resources needed by the standalone QML Kiosk."""

from __future__ import annotations

import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
QRC_PATH = BASE_DIR / "resources" / "resources.qrc"
RESOURCE_OUTPUT = BASE_DIR / "resources_rc.py"
PYTHON_DIR = Path(sys.executable).resolve().parent
TOOL_SUFFIX = ".exe" if os.name == "nt" else ""
RCC = PYTHON_DIR / f"pyside6-rcc{TOOL_SUFFIX}"


def _resource_input_paths() -> tuple[Path, ...]:
    """Return the QRC manifest and every file embedded by that manifest."""
    if not QRC_PATH.is_file():
        raise FileNotFoundError(f"Qt resource collection not found: {QRC_PATH}")

    try:
        root = ET.parse(QRC_PATH).getroot()
    except ET.ParseError as exc:
        raise RuntimeError(f"Could not parse Qt resource collection: {QRC_PATH}") from exc

    sources = [QRC_PATH]
    for file_element in root.findall(".//file"):
        relative_path = (file_element.text or "").strip()
        if not relative_path:
            continue
        source_path = (QRC_PATH.parent / relative_path).resolve()
        if not source_path.is_file():
            raise FileNotFoundError(
                f"Qt resource file declared in {QRC_PATH} does not exist: {source_path}"
            )
        sources.append(source_path)
    return tuple(sources)


def convert_qrc_file_to_python(*, force: bool = False) -> None:
    """Generate the resource module if missing, stale, or explicitly forced.

    The QML source itself must be checked: the .qrc manifest often stays unchanged
    while its referenced QML file changes. Development and packaging launchers force
    a rebuild so a stale resources_rc.py can never silently hide current UI changes.
    """
    source_paths = _resource_input_paths()
    output_exists = RESOURCE_OUTPUT.is_file()
    should_rebuild = force or not output_exists
    if output_exists and not should_rebuild:
        output_mtime_ns = RESOURCE_OUTPUT.stat().st_mtime_ns
        should_rebuild = any(
            source_path.stat().st_mtime_ns > output_mtime_ns
            for source_path in source_paths
        )

    if should_rebuild:
        if not RCC.is_file():
            raise FileNotFoundError(
                f"Required Qt resource compiler was not found: {RCC}. "
                "Make sure PySide6 is installed in the active Python environment."
            )
        print(f"Converting: {QRC_PATH.relative_to(BASE_DIR)} -> resources_rc.py")
        subprocess.run(
            [str(RCC), str(QRC_PATH), "-o", str(RESOURCE_OUTPUT)],
            cwd=BASE_DIR,
            check=True,
        )


if __name__ == "__main__":
    convert_qrc_file_to_python()

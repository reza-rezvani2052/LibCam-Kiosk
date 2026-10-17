# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

import PySide6
from PyInstaller.building.datastruct import Tree

ROOT = Path(SPEC).resolve().parent
sys.path.insert(0, str(ROOT))

from app.components.member_photo_kiosk.model_assets import is_model_file_valid
ENTRY_POINT = ROOT / "kiosk_main.py"
ICON = ROOT / "resources" / "images" / "app-icon.ico"
FACE_MODEL = ROOT / "models" / "yolo" / "yolov8n-face-lindevs.pt"
POSE_MODEL = ROOT / "models" / "yolo" / "yolo26n-pose.pt"
QML_IMPORTS = Path(PySide6.__file__).resolve().parent / "qml"

for required_file in (ENTRY_POINT, ICON, FACE_MODEL, POSE_MODEL):
    if not required_file.is_file():
        raise FileNotFoundError(f"Required Kiosk build input is missing: {required_file}")
    if required_file in (FACE_MODEL, POSE_MODEL) and not is_model_file_valid(required_file):
        raise FileNotFoundError(
            "Model file is empty or an unresolved Git LFS pointer: "
            f"{required_file}"
        )
if not QML_IMPORTS.is_dir():
    raise FileNotFoundError(f"Qt Quick QML runtime modules were not found: {QML_IMPORTS}")

analysis = Analysis(
    [str(ENTRY_POINT)],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuickControls2",
        "PySide6.QtMultimedia",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "insightface",
        "playwright",
        "matplotlib",
        "pandas",
        "scipy",
        "skimage",
        "notebook",
        "IPython",
        "pytest",
        "sphinx",
        "tkinter",
    ],
    noarchive=False,
)

# Tree produces PyInstaller TOC entries; add them after Analysis instead of
# passing them to Analysis(datas=...), which expects (source, destination) pairs.
analysis.datas += Tree(str(QML_IMPORTS), prefix="PySide6/qml")

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="LibCamKiosk",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ICON),
)

bundle = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="LibCamKiosk",
)

from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class KioskUiConfigurationTests(unittest.TestCase):
    def test_kiosk_spec_uses_current_pyside_qml_directory(self) -> None:
        spec = (ROOT / "LibCamKiosk.spec").read_text(encoding="utf-8")

        self.assertIn('QML_IMPORTS = Path(PySide6.__file__).resolve().parent / "qml"', spec)
        self.assertIn('analysis.datas += Tree(str(QML_IMPORTS), prefix="PySide6/qml")', spec)
        self.assertNotIn('Tree(str(QML_IMPORTS), prefix="PySide6/qml"),\n    ],', spec)
        self.assertNotIn('"Qt" / "qml"', spec)
        self.assertNotIn('contents_directory="."', spec)
        self.assertNotIn('(str(FACE_MODEL), "models/yolo")', spec)
        self.assertNotIn('(str(POSE_MODEL), "models/yolo")', spec)

        build_script = (ROOT / "tools" / "build" / "build_kiosk_exe.py").read_text(encoding="utf-8")
        self.assertIn("def copy_runtime_models(", build_script)
        self.assertIn('Path(bundle_directory) / "models" / "yolo"', build_script)

    def test_qml_screen_is_embedded_in_resources(self) -> None:
        qml_file = ROOT / "qml" / "KioskMain.qml"
        qrc_file = (ROOT / "resources" / "resources.qrc").read_text(encoding="utf-8")
        builder = (ROOT / "tools" / "build" / "build_qml_resources.py").read_text(encoding="utf-8")

        self.assertTrue(qml_file.is_file())
        self.assertIn('alias="qml/KioskMain.qml"', qrc_file)
        self.assertIn("_resource_input_paths", builder)
        self.assertIn("convert_qrc_file_to_python(force=True)", (ROOT / "run_kiosk_dev.py").read_text(encoding="utf-8"))
        qml_content = qml_file.read_text(encoding="utf-8")
        self.assertIn("QtQuick.Controls", qml_content)
        self.assertIn('source: "qrc:/images/app-icon.ico"', qml_content)
        self.assertNotIn('text: "LC"', qml_content)

    def test_resource_builder_rebuilds_when_referenced_qml_is_newer_than_output(self) -> None:
        from tools.build import build_qml_resources

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            resources_dir = root / "resources"
            qml_dir = root / "qml"
            resources_dir.mkdir()
            qml_dir.mkdir()

            qrc_file = resources_dir / "resources.qrc"
            qml_file = qml_dir / "KioskMain.qml"
            output_file = root / "resources_rc.py"
            compiler = root / "pyside6-rcc"
            qrc_file.write_text(
                "<RCC><qresource prefix='/'><file alias='qml/KioskMain.qml'>../qml/KioskMain.qml</file></qresource></RCC>",
                encoding="utf-8",
            )
            qml_file.write_text("ApplicationWindow {}", encoding="utf-8")
            output_file.write_text("# old generated resource module", encoding="utf-8")
            compiler.write_text("", encoding="utf-8")

            # Simulate the bug: the manifest/output timestamps are newer than the QML
            # content, even though that content has changed since resources_rc.py was built.
            now = time.time_ns()
            os.utime(qrc_file, ns=(now - 4_000_000_000, now - 4_000_000_000))
            os.utime(output_file, ns=(now - 2_000_000_000, now - 2_000_000_000))
            os.utime(qml_file, ns=(now, now))

            with (
                patch.object(build_qml_resources, "BASE_DIR", root),
                patch.object(build_qml_resources, "QRC_PATH", qrc_file),
                patch.object(build_qml_resources, "RESOURCE_OUTPUT", output_file),
                patch.object(build_qml_resources, "RCC", compiler),
                patch.object(build_qml_resources.subprocess, "run") as run,
            ):
                build_qml_resources.convert_qrc_file_to_python()

            run.assert_called_once()
            self.assertIn(str(qrc_file), run.call_args.args[0])
            self.assertIn(str(output_file), run.call_args.args[0])

    def test_kiosk_starts_in_a_normal_resizable_window(self) -> None:
        entry_point = (ROOT / "kiosk_main.py").read_text(encoding="utf-8")
        qml = (ROOT / "qml" / "KioskMain.qml").read_text(encoding="utf-8")

        self.assertIn('engine.load(QUrl("qrc:/qml/KioskMain.qml"))', entry_point)
        self.assertNotIn("showFullScreen", entry_point)
        self.assertIn("width: 1220", qml)
        self.assertIn("minimumWidth: 960", qml)
        self.assertIn("visible: true", qml)

    def test_qml_exposes_capture_review_and_save_states(self) -> None:
        qml = (ROOT / "qml" / "KioskMain.qml").read_text(encoding="utf-8")
        controller = (
            ROOT / "app" / "components" / "member_photo_kiosk" / "ui" / "kiosk_window.py"
        ).read_text(encoding="utf-8")

        for name in ("VideoFrameItem", "QtQuick.Layouts", "RotationAnimation", "Dialog"):
            self.assertIn(name, qml)
        for name in ("captureManually", "savePhoto", "retakePhoto", "startNextMember"):
            self.assertIn(name, controller)
        self.assertNotIn("Ui_KioskWindow", controller)
        self.assertNotIn("QMainWindow", controller)

    def test_qml_uses_fixed_line_height_and_separate_action_bar(self) -> None:
        qml = (ROOT / "qml" / "KioskMain.qml").read_text(encoding="utf-8")

        self.assertIn("lineHeightMode: Text.FixedHeight", qml)
        self.assertIn('objectName: "actionBar"', qml)
        self.assertIn('objectName: "captureButton"', qml)
        self.assertIn('visible: kiosk.isLive', qml)

    def test_development_entrypoint_allows_virtual_but_packaged_default_rejects_it(self) -> None:
        entry_point = (ROOT / "kiosk_main.py").read_text(encoding="utf-8")
        development_launcher = (ROOT / "run_kiosk_dev.py").read_text(encoding="utf-8")
        window_source = (
            ROOT / "app" / "components" / "member_photo_kiosk" / "ui" / "kiosk_window.py"
        ).read_text(encoding="utf-8")

        self.assertIn("allow_virtual_cameras: bool = False", entry_point)
        self.assertIn("KioskController(allow_virtual_cameras=allow_virtual_cameras)", entry_point)
        self.assertIn("main(allow_virtual_cameras=True)", development_launcher)
        self.assertIn("allow_virtual_cameras=self._allow_virtual_cameras", window_source)

    def test_kiosk_branch_does_not_retain_full_application_entrypoints(self) -> None:
        obsolete_paths = (
            "main.py", "run_dev.py", "gallery_builder_entry.py", "LibCam.spec",
            "requirements.txt", "tools/build/build_exe.py", "tools/build/bundle_playwright.py",
            "tools/benchmark_imports.py", "tools/build/build_ui_qrc.py",
            "app/components/member_photo_kiosk/ui/kiosk_window.ui",
            "app/components/member_photo_kiosk/ui/kiosk.qss",
        )
        for relative_path in obsolete_paths:
            with self.subTest(path=relative_path):
                self.assertFalse((ROOT / relative_path).exists(), relative_path)
        self.assertTrue((ROOT / "kiosk_main.py").is_file())
        self.assertTrue((ROOT / "run_kiosk_dev.py").is_file())
        self.assertTrue((ROOT / "LibCamKiosk.spec").is_file())

    def test_kiosk_has_a_separate_qml_build_spec(self) -> None:
        self.assertTrue((ROOT / "LibCamKiosk.spec").is_file())
        self.assertTrue((ROOT / "kiosk_main.py").is_file())
        self.assertTrue((ROOT / "requirements-kiosk.txt").is_file())
        self.assertTrue((ROOT / "tools" / "build" / "build_qml_resources.py").is_file())


    def test_instruction_panel_uses_the_kiosk_dark_theme(self) -> None:
        qml = (ROOT / "qml" / "KioskMain.qml").read_text(encoding="utf-8")
        start = qml.index("id: instructionPanel")
        end = qml.index("id: previewCard", start)
        panel = qml[start:end]

        self.assertIn('color: "#14243a"', panel)
        self.assertIn('border.color: "#26374c"', panel)
        self.assertIn('color: "#f1f6fb"', panel)
        self.assertIn('color: "#a5b8ca"', panel)
        self.assertIn('kiosk.statusError ? "#3b202d" : "#152c40"', panel)
        self.assertNotIn('color: "#f4f7fb"', panel)
        self.assertNotIn('border.color: "#ffffff"', panel)


if __name__ == "__main__":
    unittest.main()

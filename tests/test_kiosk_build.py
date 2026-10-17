from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import patch

from tools.build import build_kiosk_exe
from app.components.member_photo_kiosk.model_assets import is_model_file_available


class KioskBuildDurationTests(unittest.TestCase):
    def test_elapsed_time_is_formatted_as_hours_minutes_seconds(self) -> None:
        cases = (
            (0, "00:00:00"),
            (65.9, "00:01:05"),
            (3661, "01:01:01"),
        )
        for elapsed, expected in cases:
            with self.subTest(elapsed=elapsed):
                self.assertEqual(build_kiosk_exe._format_elapsed_time(elapsed), expected)

    def test_model_weights_are_copied_beside_executable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_directory = root / "source-models"
            source_directory.mkdir()
            face_source = source_directory / "yolov8n-face-lindevs.pt"
            pose_source = source_directory / "yolo26n-pose.pt"
            face_source.write_bytes(b"face model weights")
            pose_source.write_bytes(b"pose model weights")

            bundle_directory = root / "LibCamKiosk"
            bundle_directory.mkdir()

            with (
                patch.object(build_kiosk_exe, "face_model_path", return_value=face_source),
                patch.object(build_kiosk_exe, "pose_model_path", return_value=pose_source),
            ):
                destination = build_kiosk_exe.copy_runtime_models(bundle_directory)

            self.assertEqual(destination, bundle_directory / "models" / "yolo")
            self.assertEqual(
                (destination / face_source.name).read_bytes(),
                face_source.read_bytes(),
            )
            self.assertEqual(
                (destination / pose_source.name).read_bytes(),
                pose_source.read_bytes(),
            )
            self.assertFalse((bundle_directory / "_internal" / "models").exists())

    def test_duration_is_printed_when_build_preparation_fails(self) -> None:
        stdout = StringIO()
        stderr = StringIO()

        with (
            patch.object(build_kiosk_exe.time, "perf_counter", side_effect=[10.0, 13.8]),
            patch.object(
                build_kiosk_exe,
                "check_model_files",
                side_effect=FileNotFoundError("missing model for test"),
            ),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            result = build_kiosk_exe.main()

        self.assertEqual(result, 1)
        self.assertIn("Build duration: 00:00:03", stdout.getvalue())
        self.assertIn("Kiosk build failed", stderr.getvalue())


class ModelAssetValidationTests(unittest.TestCase):
    def test_model_file_validation_rejects_missing_empty_and_lfs_pointer_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            missing_path = root / "missing.pt"
            empty_path = root / "empty.pt"
            lfs_pointer_path = root / "pointer.pt"
            small_local_file_path = root / "small-local-file.pt"

            empty_path.write_bytes(b"")
            lfs_pointer_path.write_text(
                "version https://git-lfs.github.com/spec/v1\n"
                "oid sha256:0123456789abcdef\n"
                "size 123456\n",
                encoding="utf-8",
            )
            # No arbitrary file-size threshold is applied.
            small_local_file_path.write_bytes(b"local model content")

            self.assertFalse(is_model_file_available(missing_path))
            self.assertFalse(is_model_file_available(empty_path))
            self.assertFalse(is_model_file_available(lfs_pointer_path))
            self.assertTrue(is_model_file_available(small_local_file_path))

    def test_model_assets_and_launchers_contain_no_download_implementation(self) -> None:
        root = Path(__file__).resolve().parents[1]
        relative_paths = (
            "app/components/member_photo_kiosk/model_assets.py",
            "run_kiosk_dev.py",
            "tools/build/build_kiosk_exe.py",
        )
        forbidden_tokens = (
            "urlopen",
            "urlretrieve",
            "urllib",
            "POSE_MODEL_URL",
            "ensure_pose_model",
            "MINIMUM_MODEL_BYTES",
        )

        for relative_path in relative_paths:
            source = (root / relative_path).read_text(encoding="utf-8")
            for token in forbidden_tokens:
                with self.subTest(path=relative_path, token=token):
                    self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()

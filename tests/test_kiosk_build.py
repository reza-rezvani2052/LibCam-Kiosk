from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import patch

from tools.build import build_kiosk_exe


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
            face_source.write_bytes(b"f" * (build_kiosk_exe.MINIMUM_MODEL_BYTES + 1))
            pose_source.write_bytes(b"p" * (build_kiosk_exe.MINIMUM_MODEL_BYTES + 1))

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
                "check_face_model",
                side_effect=FileNotFoundError("missing model for test"),
            ),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            result = build_kiosk_exe.main()

        self.assertEqual(result, 1)
        self.assertIn("Build duration: 00:00:03", stdout.getvalue())
        self.assertIn("Kiosk build failed", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

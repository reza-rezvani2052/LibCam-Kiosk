"""Hardware-facing webcam controller."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

import cv2

from PySide6.QtCore import QObject, Signal
from PySide6.QtMultimedia import QMediaDevices

logger = logging.getLogger(__name__)


if os.name == "nt":
    try:
        from pygrabber.dshow_graph import FilterGraph
    except ImportError:
        FilterGraph = None
else:
    FilterGraph = None


@dataclass(frozen=True, slots=True)
class CameraDevice:
    """Normalized camera information used by the UI."""

    description: str
    camera_id: bytes
    dshow_index: int | None


class CameraController(QObject):
    """Enumerate, open, read and release the application's webcam."""

    video_inputs_changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        self._capture = cv2.VideoCapture()
        self._media_devices = QMediaDevices(self)
        self._last_error_message = ""
        self._media_devices.videoInputsChanged.connect(
                self.video_inputs_changed.emit
                )

    @property
    def is_opened(self) -> bool:
        return self._capture.isOpened()

    @property
    def last_error_message(self) -> str:
        return self._last_error_message

    @property
    def backend_name(self) -> str:
        if not self.is_opened:
            return ""

        return self._capture.getBackendName()

    @staticmethod
    def _normalize_camera_name(name: str) -> str:
        return " ".join(name.strip().casefold().split())

    @staticmethod
    def _get_direct_show_camera_names() -> list[str]:
        if FilterGraph is None:
            logger.warning(
                    "DirectShow camera enumeration is unavailable; "
                    "falling back to Qt camera enumeration."
                    )
            return []

        try:
            graph = FilterGraph()
            return list(graph.get_input_devices())
        except Exception:  # noqa: BLE001
            logger.exception("Failed to enumerate DirectShow cameras.")
            return []

    def list_devices(self) -> list[CameraDevice]:
        devices: list[CameraDevice] = []

        qt_cameras = list(QMediaDevices.videoInputs())
        dshow_names = self._get_direct_show_camera_names()

        dshow_indexes_by_name: dict[str, list[int]] = {}

        for dshow_index, name in enumerate(dshow_names):
            key = self._normalize_camera_name(name)
            dshow_indexes_by_name.setdefault(key, []).append(dshow_index)

        for qt_index, camera in enumerate(qt_cameras):
            description = camera.description() or "Camera"
            camera_id = bytes(camera.id())
            key = self._normalize_camera_name(description)

            dshow_indexes = dshow_indexes_by_name.get(key, [])
            dshow_index = dshow_indexes.pop(0) if dshow_indexes else None

            if dshow_index is None:
                logger.warning(
                        "No DirectShow index found for Qt camera: %s",
                        description,
                        )

                if qt_index < len(dshow_names):
                    dshow_index = qt_index

            devices.append(
                    CameraDevice(
                            description=description,
                            camera_id=camera_id,
                            dshow_index=dshow_index,
                            )
                    )

        return devices

    def open(self, *, index: int, description: str) -> bool:
        self._last_error_message = ""

        if self.is_opened:
            self.release()

        logger.info(
                "Opening camera: index=%s, description=%s, backend=DSHOW",
                index, description,
                )

        open_started = time.perf_counter()
        opened = self._capture.open(index, cv2.CAP_DSHOW)
        open_elapsed = time.perf_counter() - open_started

        if not opened or not self.is_opened:
            self._last_error_message = "دسترسی به وب‌کم ممکن نیست"
            logger.warning(
                    "Camera open failed: index=%s, elapsed=%.3fs",
                    index, open_elapsed
                    )
            return False

        read_started = time.perf_counter()
        ok, _ = self.read()
        read_elapsed = time.perf_counter() - read_started

        if not ok:
            self._last_error_message = "دریافت تصویر از وب‌کم ممکن نیست"
            logger.warning(
                    "Initial camera read failed: index=%s, "
                    "open_elapsed=%.3fs, read_elapsed=%.3fs",
                    index, open_elapsed, read_elapsed
                    )
            self.release()
            return False

        logger.info(
                "Camera ready: index=%s, backend=%s, "
                "open_elapsed=%.3fs, read_elapsed=%.3fs",
                index, self.backend_name, open_elapsed, read_elapsed
                )

        return True

    def read(self):
        return self._capture.read()

    def release(self) -> None:
        if self.is_opened:
            self._capture.release()

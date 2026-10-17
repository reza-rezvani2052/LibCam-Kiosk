"""Background pose detection and face-photo capture for the kiosk."""

from __future__ import annotations

import logging
import threading
import time

import numpy as np
from PySide6.QtCore import QObject, QThread, Signal

from app.components.member_photo_kiosk.core.gesture_detector import (
    HandRaiseDetector,
    is_hand_raised,
)
from app.components.member_photo_kiosk.core.image_cropper import crop_detected_face
from app.components.member_photo_kiosk.model_assets import is_model_file_available
from app.components.member_photo_kiosk.paths import face_model_path, pose_model_path

logger = logging.getLogger("libcam_kiosk")


class KioskVisionWorker(QObject):
    """Load YOLO models off the UI thread and process only the newest camera frame."""

    models_ready = Signal()
    capture_started = Signal(str)
    photo_ready = Signal(object, str)
    capture_failed = Signal(str)
    error = Signal(str)
    finished = Signal()

    POSE_INTERVAL_SECONDS = 0.22
    POSE_CONFIDENCE = 0.25
    FACE_CONFIDENCE = 0.35
    INFERENCE_SIZE = 416
    FACE_CAPTURE_SIZE = 640

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.pose_path = pose_model_path()
        self.face_path = face_model_path()
        self._pose_model = None
        self._face_model = None
        self._lock = threading.Lock()
        self._latest_frame: np.ndarray | None = None
        self._last_frame: np.ndarray | None = None
        self._manual_request: str | None = None
        self._paused = False
        self._stop_requested = False
        self._gesture_detector = HandRaiseDetector()

    def submit_frame(self, frame: np.ndarray) -> None:
        """Keep only the newest frame; do not build a queue of stale frames."""
        if frame is None or frame.size == 0:
            return
        with self._lock:
            if self._stop_requested:
                return
            frame_copy = frame.copy()
            self._last_frame = frame_copy
            if not self._paused:
                self._latest_frame = frame_copy

    def request_capture(self, source: str = "manual") -> bool:
        """Queue a manual capture request without blocking the UI thread."""
        with self._lock:
            if self._stop_requested or self._paused or self._manual_request is not None:
                return False
            self._manual_request = source
            return True

    def resume_detection(self) -> None:
        """Resume pose checks after the user asks to retake or start a new photo."""
        with self._lock:
            if self._stop_requested:
                return
            self._paused = False
            self._latest_frame = None

    def stop(self) -> None:
        with self._lock:
            self._stop_requested = True
            self._latest_frame = None
            self._last_frame = None
            self._manual_request = None

    def _state(self) -> tuple[bool, bool]:
        with self._lock:
            return self._stop_requested, self._paused

    def _take_work(self) -> tuple[np.ndarray | None, str | None]:
        with self._lock:
            if self._stop_requested:
                return None, None
            if self._manual_request is not None:
                source = self._manual_request
                self._manual_request = None
                frame = self._latest_frame
                if frame is None:
                    frame = self._last_frame
                self._latest_frame = None
                return frame, source
            if self._paused:
                return None, None
            frame = self._latest_frame
            self._latest_frame = None
            return frame, None

    def _load_models(self) -> bool:
        missing = [
            path for path in (self.pose_path, self.face_path)
            if not is_model_file_available(path)
        ]
        if missing:
            paths = "\n".join(str(path) for path in missing)
            self.error.emit(
                "فایل مدل موردنیاز پیدا نشد، خالی است یا فایل اشاره‌گر Git LFS است:\n"
                f"{paths}\n\n"
                "هر دو فایل مدل باید از قبل در پوشه models/yolo کنار برنامه قرار داشته باشند. "
                "برنامه هیچ فایلی را از اینترنت دانلود نمی‌کند."
            )
            return False

        try:
            # The costly inference dependency is imported only in this background thread.
            from ultralytics import YOLO

            logger.info("Loading kiosk pose model: %s", self.pose_path)
            self._pose_model = YOLO(str(self.pose_path))
            logger.info("Loading kiosk face model: %s", self.face_path)
            self._face_model = YOLO(str(self.face_path))
            logger.info("Kiosk vision models loaded.")
            self.models_ready.emit()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.exception("Could not load kiosk vision models.")
            self.error.emit(f"بارگذاری مدل‌های تشخیص تصویر ناموفق بود:\n{exc}")
            self._pose_model = None
            self._face_model = None
            return False

    @staticmethod
    def _to_list(tensor) -> list:
        if tensor is None:
            return []
        if hasattr(tensor, "detach"):
            tensor = tensor.detach()
        if hasattr(tensor, "cpu"):
            tensor = tensor.cpu()
        if hasattr(tensor, "tolist"):
            return tensor.tolist()
        return list(tensor)

    def _detect_raised_hand(self, frame: np.ndarray) -> bool:
        if self._pose_model is None:
            return False
        results = self._pose_model.predict(
            source=frame,
            conf=self.POSE_CONFIDENCE,
            imgsz=self.INFERENCE_SIZE,
            verbose=False,
            device="cpu",
        )
        if not results:
            return False
        result = results[0]
        if result.keypoints is None or result.keypoints.data is None:
            return False

        people = self._to_list(result.keypoints.data)
        if not people:
            return False

        if result.boxes is not None and len(result.boxes) == len(people):
            boxes = self._to_list(result.boxes.xyxy)
            if boxes:
                areas = [
                    max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])
                    for box in boxes
                ]
                person_index = max(range(len(areas)), key=areas.__getitem__)
            else:
                person_index = 0
        else:
            person_index = 0

        return is_hand_raised(people[person_index], frame.shape[0])

    def _capture_photo(self, frame: np.ndarray, source: str) -> None:
        with self._lock:
            if self._stop_requested:
                return
            self._paused = True
            self._latest_frame = None
        self._gesture_detector.disarm()
        self.capture_started.emit(source)

        try:
            results = self._face_model.predict(
                source=frame,
                conf=self.FACE_CONFIDENCE,
                imgsz=self.FACE_CAPTURE_SIZE,
                verbose=False,
                device="cpu",
            )
            result = results[0] if results else None
            if result is None or result.boxes is None or len(result.boxes) == 0:
                self._resume_after_failed_capture()
                self.capture_failed.emit(
                    "چهره‌ای در تصویر پیدا نشد. روبه‌روی دوربین قرار بگیرید و دوباره تلاش کنید."
                )
                return

            boxes = self._to_list(result.boxes.xyxy)
            if not boxes:
                self._resume_after_failed_capture()
                self.capture_failed.emit(
                    "محدوده‌ی چهره تشخیص داده نشد. لطفاً دوباره عکس بگیرید."
                )
                return

            # If multiple faces are visible, use the largest detected face.
            face_box = max(
                boxes,
                key=lambda box: max(0.0, box[2] - box[0])
                * max(0.0, box[3] - box[1]),
            )
            crop = crop_detected_face(frame, face_box)
            if crop is None:
                self._resume_after_failed_capture()
                self.capture_failed.emit(
                    "کادر چهره کامل نیست. کمی در مرکز تصویر قرار بگیرید و دوباره تلاش کنید."
                )
                return

            self.photo_ready.emit(crop, source)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Face-photo capture failed.")
            self._resume_after_failed_capture()
            self.capture_failed.emit(f"پردازش عکس ناموفق بود:\n{exc}")

    def _resume_after_failed_capture(self) -> None:
        with self._lock:
            if not self._stop_requested:
                self._paused = False
                self._latest_frame = None
        # Require a lowered hand before the next automatic capture.
        self._gesture_detector.disarm()

    def run(self) -> None:
        """Thread entry point. Inference errors are surfaced and stop this worker."""
        if not self._load_models():
            self.finished.emit()
            return

        last_pose_time = 0.0
        try:
            while True:
                stopped, _paused = self._state()
                if stopped:
                    break

                frame, requested_source = self._take_work()
                if requested_source is not None:
                    if frame is None:
                        self.capture_failed.emit("تصویری از وب‌کم دریافت نشده است.")
                    else:
                        self._capture_photo(frame, requested_source)
                    continue

                if frame is None:
                    QThread.msleep(8)
                    continue

                now = time.monotonic()
                if now - last_pose_time < self.POSE_INTERVAL_SECONDS:
                    continue
                last_pose_time = now

                try:
                    raised = self._detect_raised_hand(frame)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("YOLO pose inference failed.")
                    self.error.emit(f"تشخیص ژست دست ناموفق بود:\n{exc}")
                    break

                if self._gesture_detector.update(raised, now):
                    self._capture_photo(frame, "gesture")
        finally:
            self.finished.emit()

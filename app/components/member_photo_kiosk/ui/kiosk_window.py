"""Qt Quick backend and accelerated canvas item for the Kiosk preview."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import (
    QObject,
    Property,
    QStandardPaths,
    QThread,
    QTimer,
    QUrl,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QDesktopServices, QImage, QPainter
from PySide6.QtCore import QRectF
from PySide6.QtQuick import QQuickPaintedItem

from app.components.member_photo_kiosk.core.camera_policy import is_camera_allowed
from app.components.member_photo_kiosk.core.vision_worker import KioskVisionWorker
from app.infrastructure.camera.controller import CameraController

logger = logging.getLogger("libcam_kiosk")


class VideoFrameItem(QQuickPaintedItem):
    """Paint camera frames into a Qt Quick scene while preserving aspect ratio."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._image = QImage()
        self.setAntialiasing(True)
        self.setOpaquePainting(False)
        # Qt 6.9+ accelerates QPainter rendering with OpenGL; other backends ignore this target.
        self.setRenderTarget(QQuickPaintedItem.RenderTarget.FramebufferObject)

    def set_frame(self, frame: np.ndarray, *, mirror: bool = True) -> None:
        """Set a frame from OpenCV; callers must invoke this on the GUI thread."""
        if frame is None or frame.size == 0:
            self._image = QImage()
            self.update()
            return

        display_frame = cv2.flip(frame, 1) if mirror else frame
        rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        image = QImage(
            rgb.data,
            rgb.shape[1],
            rgb.shape[0],
            rgb.strides[0],
            QImage.Format.Format_RGB888,
        )
        self._image = image.copy()
        self.update()

    @Slot()
    def clear_frame(self) -> None:
        self._image = QImage()
        self.update()

    def paint(self, painter: QPainter) -> None:
        if self._image.isNull():
            return

        bounds = self.boundingRect()
        if bounds.width() <= 0 or bounds.height() <= 0:
            return

        scale = min(
            bounds.width() / self._image.width(),
            bounds.height() / self._image.height(),
        )
        width = self._image.width() * scale
        height = self._image.height() * scale
        target = QRectF(
            bounds.x() + (bounds.width() - width) / 2,
            bounds.y() + (bounds.height() - height) / 2,
            width,
            height,
        )
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(target, self._image)


class KioskController(QObject):
    """Stateful backend exposed to QML; all camera and file actions live here."""

    statusChanged = Signal()
    uiStateChanged = Signal()

    CAMERA_TIMER_INTERVAL_MS = 33

    def __init__(
        self,
        *,
        allow_virtual_cameras: bool = False,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._allow_virtual_cameras = allow_virtual_cameras
        self.camera = CameraController(self)
        self._video_item: VideoFrameItem | None = None
        self._camera_read_failures = 0
        self._vision_ready = False
        self._camera_ready = False
        self._mode = "live"
        self._status_text = "در حال آماده‌سازی برنامه…"
        self._status_error = False
        self._captured_image: np.ndarray | None = None
        self._saved_photo: Path | None = None
        self._output_file = self._get_output_file()
        self._privacy_cleanup_ok = True
        self._started = False
        self._shutting_down = False
        self._vision_thread: QThread | None = None
        self._vision_worker: KioskVisionWorker | None = None

        self._camera_timer = QTimer(self)
        self._camera_timer.setInterval(self.CAMERA_TIMER_INTERVAL_MS)
        self._camera_timer.timeout.connect(self._update_camera_frame)

    statusText = Property(str, lambda self: self._status_text, notify=statusChanged)
    statusError = Property(bool, lambda self: self._status_error, notify=statusChanged)
    mode = Property(str, lambda self: self._mode, notify=uiStateChanged)
    cameraReady = Property(bool, lambda self: self._camera_ready, notify=uiStateChanged)
    visionReady = Property(bool, lambda self: self._vision_ready, notify=uiStateChanged)
    isLive = Property(bool, lambda self: self._mode == "live", notify=uiStateChanged)
    isProcessing = Property(bool, lambda self: self._mode == "processing", notify=uiStateChanged)
    isReview = Property(bool, lambda self: self._mode == "review", notify=uiStateChanged)
    isSaved = Property(bool, lambda self: self._mode == "saved", notify=uiStateChanged)
    canCapture = Property(
        bool,
        lambda self: (
            self._mode == "live"
            and self._camera_ready
            and self._vision_ready
            and self._privacy_cleanup_ok
            and self._vision_worker is not None
        ),
        notify=uiStateChanged,
    )
    hasCapturedPhoto = Property(
        bool, lambda self: self._captured_image is not None, notify=uiStateChanged
    )
    outputPath = Property(str, lambda self: str(self._output_file), constant=True)

    @staticmethod
    def _get_output_file() -> Path:
        pictures_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.PicturesLocation
        )
        base_dir = Path(pictures_dir) if pictures_dir else Path.home() / "Pictures"
        return base_dir / "LibCam Kiosk" / "samanpl.jpg"

    @Slot(QObject)
    def attachVideoItem(self, item: QObject) -> None:  # noqa: N802
        """Receive the QML video surface before the camera runtime starts."""
        if isinstance(item, VideoFrameItem):
            self._video_item = item

    @Slot()
    def start(self) -> None:
        """Initialize the camera and vision worker after the QML scene is loaded."""
        if self._started:
            return
        self._started = True
        self._privacy_cleanup_ok = self._remove_previous_photo_at_startup()
        if not self._privacy_cleanup_ok:
            self._set_status(
                "عکس قبلی پاک نشد؛ برای حفظ حریم خصوصی، ثبت عکس غیرفعال است.",
                error=True,
            )

        if self._privacy_cleanup_ok:
            self._set_status("در حال آماده‌سازی دوربین و مدل‌های تشخیص تصویر…")

        self._start_vision_worker()
        self._open_camera()

    def _remove_previous_photo_at_startup(self) -> bool:
        """Remove only Kiosk-owned output, never other files in the directory."""
        try:
            for path in (
                self._output_file,
                self._output_file.with_name("samanpl.tmp.jpg"),
            ):
                path.unlink(missing_ok=True)
            return True
        except OSError:
            logger.exception("Could not remove a stale kiosk photo.")
            return False

    def _start_vision_worker(self) -> None:
        self._vision_thread = QThread(self)
        self._vision_worker = KioskVisionWorker()
        self._vision_worker.moveToThread(self._vision_thread)
        self._vision_thread.started.connect(self._vision_worker.run)
        self._vision_worker.models_ready.connect(self._on_models_ready)
        self._vision_worker.capture_started.connect(self._on_capture_started)
        self._vision_worker.photo_ready.connect(self._on_photo_ready)
        self._vision_worker.capture_failed.connect(self._on_capture_failed)
        self._vision_worker.error.connect(self._on_vision_error)
        self._vision_worker.finished.connect(self._vision_thread.quit)
        self._vision_thread.finished.connect(self._on_vision_thread_finished)
        self._vision_thread.finished.connect(self._vision_worker.deleteLater)
        self._vision_thread.start()

    def _open_camera(self) -> None:
        """Open the first camera allowed by the current runtime policy."""
        self.camera.release()
        self._camera_timer.stop()
        devices = self.camera.list_devices()
        candidates = [
            (position, device)
            for position, device in enumerate(devices)
            if is_camera_allowed(
                device.description,
                allow_virtual_cameras=self._allow_virtual_cameras,
            )
        ]

        if not candidates:
            self._set_camera_ready(False)
            if self._allow_virtual_cameras:
                message = (
                    "وب‌کمی پیدا نشد. برای توسعه می‌توانی ManyCam Virtual Webcam "
                    "یا یک وب‌کم دیگر را فعال کنی."
                )
            else:
                message = (
                    "وب‌کم فیزیکی پیدا نشد. یک وب‌کم واقعی به رایانه متصل کنید؛ "
                    "وب‌کم‌های مجازی در نسخهٔ نهایی پشتیبانی نمی‌شوند."
                )
            if self._video_item is not None:
                self._video_item.clear_frame()
            self._set_status(message, error=True)
            return

        last_error = ""
        for fallback_index, device in candidates:
            camera_index = (
                device.dshow_index
                if device.dshow_index is not None
                else fallback_index
            )
            self.camera.release()
            if not self.camera.open(index=int(camera_index), description=device.description):
                last_error = self.camera.last_error_message
                continue

            self._camera_read_failures = 0
            self._set_camera_ready(True)
            self._camera_timer.start()
            logger.info(
                "Kiosk camera opened: %s (index %s, virtual allowed: %s)",
                device.description,
                camera_index,
                self._allow_virtual_cameras,
            )
            if self._vision_ready:
                self._set_ready_status()
            else:
                self._set_status("دوربین آماده است؛ مدل‌های تشخیص در حال بارگذاری هستند.")
            return

        self._set_camera_ready(False)
        message = "وب‌کم پیدا شد اما باز کردن آن ناموفق بود. دسترسی دوربین را بررسی کنید. "
        self._set_status(message + last_error, error=True)

    def _update_camera_frame(self) -> None:
        if not self.camera.is_opened:
            return

        ok, frame = self.camera.read()
        if not ok or frame is None:
            self._camera_read_failures += 1
            if self._camera_read_failures >= 15:
                self._camera_timer.stop()
                self.camera.release()
                self._set_camera_ready(False)
                self._set_status(
                    "دریافت تصویر از دوربین متوقف شد؛ اتصال وب‌کم را بررسی کنید.",
                    error=True,
                )
            return

        self._camera_read_failures = 0
        if self._mode != "live":
            return
        if self._vision_ready and self._vision_worker is not None:
            self._vision_worker.submit_frame(frame)
        if self._video_item is not None:
            self._video_item.set_frame(frame, mirror=True)

    def _set_camera_ready(self, ready: bool) -> None:
        if self._camera_ready != ready:
            self._camera_ready = ready
            self.uiStateChanged.emit()

    def _set_vision_ready(self, ready: bool) -> None:
        if self._vision_ready != ready:
            self._vision_ready = ready
            self.uiStateChanged.emit()

    def _set_mode(self, mode: str) -> None:
        if self._mode != mode:
            self._mode = mode
            self.uiStateChanged.emit()

    def _set_status(self, message: str, *, error: bool = False) -> None:
        if self._status_text != message or self._status_error != error:
            self._status_text = message
            self._status_error = error
            self.statusChanged.emit()

    def _set_ready_status(self) -> None:
        if not self._privacy_cleanup_ok:
            self._set_status(
                "عکس قبلی پاک نشد؛ برای حفظ حریم خصوصی، ثبت عکس غیرفعال است.",
                error=True,
            )
            return
        self._set_status(
            "برای ثبت خودکار، یکی از دست‌ها را بالا ببرید؛ یا دکمهٔ «گرفتن عکس» را بزنید."
        )

    @Slot()
    def captureManually(self) -> None:  # noqa: N802
        if not self.canCapture or self._vision_worker is None:
            return
        if self._vision_worker.request_capture("manual"):
            self._set_mode("processing")
            self._set_status("در حال بررسی چهره و آماده‌سازی عکس…")
        else:
            self._set_status("در حال پردازش درخواست قبلی هستیم؛ کمی صبر کنید.")

    def _on_models_ready(self) -> None:
        self._set_vision_ready(True)
        logger.info("Kiosk vision worker is ready.")
        if self._camera_ready and self._mode == "live":
            self._set_ready_status()

    def _on_capture_started(self, source: str) -> None:
        self._set_mode("processing")
        self._set_status(
            "ژست دست تشخیص داده شد؛ در حال آماده‌سازی عکس…"
            if source == "gesture"
            else "در حال بررسی چهره و آماده‌سازی عکس…"
        )

    def _on_photo_ready(self, image: np.ndarray, source: str) -> None:
        self._captured_image = image.copy()
        self._saved_photo = None
        if self._video_item is not None:
            self._video_item.set_frame(self._captured_image, mirror=False)
        self._set_mode("review")
        self._set_status(
            "صورت را بررسی کنید؛ اگر کامل و واضح است، «ذخیره تصویر» را بزنید."
        )
        logger.info("Kiosk portrait prepared from %s trigger.", source)

    def _on_capture_failed(self, message: str) -> None:
        self._set_mode("live")
        if self._vision_worker is not None:
            self._vision_worker.resume_detection()
        self._set_status(message, error=True)

    def _on_vision_error(self, message: str) -> None:
        self._set_vision_ready(False)
        self._set_status(message, error=True)
        logger.error("Kiosk vision error: %s", message)

    @Slot()
    def savePhoto(self) -> None:  # noqa: N802
        if self._mode != "review" or self._captured_image is None:
            return

        temporary_path = self._output_file.with_name("samanpl.tmp.jpg")
        try:
            self._output_file.parent.mkdir(parents=True, exist_ok=True)
            written = cv2.imwrite(
                str(temporary_path),
                self._captured_image,
                [cv2.IMWRITE_JPEG_QUALITY, 95],
            )
            if not written:
                raise OSError("OpenCV could not encode the captured image as JPG.")
            os.replace(temporary_path, self._output_file)
        except (OSError, cv2.error) as exc:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                logger.exception("Could not remove temporary JPG after a failed save.")
            logger.exception("Could not save Kiosk JPG.")
            self._set_status(f"ذخیرهٔ عکس ناموفق بود:\n{exc}", error=True)
            return

        self._saved_photo = self._output_file
        self._set_mode("saved")
        self._set_status(
            "عکس با فرمت JPG ذخیره شد. اکنون آن را در سامانهٔ سامان بارگذاری کنید."
        )
        logger.info("Kiosk JPG saved to its dedicated output path.")

    @Slot()
    def retakePhoto(self) -> None:  # noqa: N802
        """Discard an un-saved preview and return to live camera mode."""
        if self._mode != "review":
            return
        self._captured_image = None
        self._begin_live_mode("برای گرفتن عکس جدید یکی از دست‌ها را بالا ببرید یا دکمه را بزنید.")

    @Slot()
    def confirmRetake(self) -> None:  # noqa: N802
        """Delete the saved JPG after QML asks the user to confirm retaking."""
        if self._mode != "saved" or not self._delete_saved_photo():
            return
        self._saved_photo = None
        self._captured_image = None
        self._begin_live_mode("عکس قبلی حذف شد؛ برای گرفتن عکس جدید آماده‌اید.")

    @Slot()
    def startNextMember(self) -> None:  # noqa: N802
        """Clear the saved image and prepare the kiosk for the next visitor."""
        if self._mode != "saved" or not self._delete_saved_photo():
            return
        self._saved_photo = None
        self._captured_image = None
        self._begin_live_mode("برای عضو بعدی، یکی از دست‌ها را بالا ببرید یا دکمهٔ گرفتن عکس را بزنید.")

    def _begin_live_mode(self, status: str) -> None:
        self._set_mode("live")
        if self._vision_worker is not None:
            self._vision_worker.resume_detection()
        if self._camera_ready and self._video_item is not None:
            self._video_item.clear_frame()
        self._set_status(status, error=not self._privacy_cleanup_ok)

    def _delete_saved_photo(self) -> bool:
        try:
            self._output_file.unlink(missing_ok=True)
            self._privacy_cleanup_ok = True
            return True
        except OSError as exc:
            self._privacy_cleanup_ok = False
            logger.exception("Could not remove the saved Kiosk photo.")
            self._set_status(
                f"پاک کردن عکس قبلی ناموفق بود؛ برای حفظ حریم خصوصی فرایند بعدی آغاز نشد:\n{exc}",
                error=True,
            )
            self.uiStateChanged.emit()
            return False

    @Slot()
    def openOutputFolder(self) -> None:  # noqa: N802
        try:
            self._output_file.parent.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._output_file.parent)))
        except OSError as exc:
            self._set_status(f"باز کردن پوشهٔ عکس ناموفق بود:\n{exc}", error=True)

    def _on_vision_thread_finished(self) -> None:
        if self._shutting_down:
            return
        if self._vision_ready:
            self._set_vision_ready(False)
            self._set_status("پردازش تصویر متوقف شد. برنامه را دوباره اجرا کنید.", error=True)

    @Slot()
    def shutdown(self) -> None:
        """Release camera and stop the background thread during application exit."""
        if self._shutting_down:
            return
        self._shutting_down = True
        self._camera_timer.stop()
        self.camera.release()
        if self._vision_thread is not None and self._vision_thread.isRunning():
            if self._vision_worker is not None:
                self._vision_worker.stop()
            self._vision_thread.quit()
            self._vision_thread.wait()

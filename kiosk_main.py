"""Entry point for the standalone Qt Quick LibCam Kiosk application."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def _configure_logging() -> None:
    local_app_data = os.environ.get("LOCALAPPDATA")
    base_dir = Path(local_app_data) if local_app_data else Path.home() / ".local" / "share"
    log_directory = base_dir / "LibCamKiosk" / "logs"
    try:
        log_directory.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
                log_directory / "libcam-kiosk.log",
                maxBytes=1_000_000,
                backupCount=3,
                encoding="utf-8",
                )
        logging.basicConfig(
                level=logging.INFO,
                handlers=[handler],
                format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                )
    except OSError:
        logging.basicConfig(level=logging.INFO)


def main(*, allow_virtual_cameras: bool = False) -> int:
    _configure_logging()

    # Register compiled Qt resources before loading the QML document.
    import resources_rc  # noqa: F401
    from PySide6.QtCore import QUrl, Qt
    from PySide6.QtGui import QGuiApplication, QIcon
    from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
    from PySide6.QtQuickControls2 import QQuickStyle

    from app.components.member_photo_kiosk.ui.kiosk_window import (
        KioskController, VideoFrameItem
        )

    app = QGuiApplication(sys.argv)
    app.setApplicationName("LibCam Kiosk")
    app.setOrganizationName("ChalusPl")
    app.setOrganizationDomain("samanpl.ir")
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    QQuickStyle.setStyle("Basic")
    qmlRegisterType(VideoFrameItem, "LibCam.Kiosk", 1, 0, "VideoFrameItem")

    engine = QQmlApplicationEngine()
    controller = KioskController(allow_virtual_cameras=allow_virtual_cameras)
    engine.rootContext().setContextProperty("kiosk", controller)
    engine.load(QUrl("qrc:/qml/KioskMain.qml"))

    root_objects = engine.rootObjects()
    if not root_objects:
        logging.getLogger("libcam_kiosk").error("The Kiosk QML scene could not be loaded.")
        controller.shutdown()
        return 1

    root_objects[0].setIcon(QIcon(":/images/app-icon.ico"))
    app.aboutToQuit.connect(controller.shutdown)
    controller.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

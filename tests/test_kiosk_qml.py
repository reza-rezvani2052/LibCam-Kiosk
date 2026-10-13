from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtQuickControls2 import QQuickStyle

import resources_rc  # noqa: F401  # generated from resources/resources.qrc by CI/dev preparation
from app.components.member_photo_kiosk.ui.kiosk_window import VideoFrameItem


class FakeKiosk(QObject):
    statusChanged = Signal()
    uiStateChanged = Signal()

    def __init__(self):
        super().__init__()
        self._video_item = None
        self._mode = "live"

    @Property(str, notify=statusChanged)
    def statusText(self):
        return "Ready"

    @Property(bool, notify=statusChanged)
    def statusError(self):
        return False

    @Property(str, notify=uiStateChanged)
    def mode(self):
        return self._mode

    @Property(bool, notify=uiStateChanged)
    def cameraReady(self):
        return True

    @Property(bool, notify=uiStateChanged)
    def visionReady(self):
        return True

    @Property(bool, notify=uiStateChanged)
    def isLive(self):
        return self._mode == "live"

    @Property(bool, notify=uiStateChanged)
    def isProcessing(self):
        return self._mode == "processing"

    @Property(bool, notify=uiStateChanged)
    def isReview(self):
        return self._mode == "review"

    @Property(bool, notify=uiStateChanged)
    def isSaved(self):
        return self._mode == "saved"

    @Property(bool, notify=uiStateChanged)
    def canCapture(self):
        return True

    @Property(bool, notify=uiStateChanged)
    def hasCapturedPhoto(self):
        return False

    @Property(str, constant=True)
    def outputPath(self):
        return "C:/Pictures/LibCam Kiosk/samanpl.jpg"

    @Slot(QObject)
    def attachVideoItem(self, item):
        self._video_item = item

    @Slot(str)
    def setMode(self, mode):
        self._mode = mode
        self.uiStateChanged.emit()

    @Slot()
    def captureManually(self): pass

    @Slot()
    def savePhoto(self): pass

    @Slot()
    def retakePhoto(self): pass

    @Slot()
    def confirmRetake(self): pass

    @Slot()
    def startNextMember(self): pass

    @Slot()
    def openOutputFolder(self): pass


class KioskQmlSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication([])
        cls.app.setQuitOnLastWindowClosed(False)
        QQuickStyle.setStyle("Basic")
        qmlRegisterType(VideoFrameItem, "LibCam.Kiosk", 1, 0, "VideoFrameItem")
        cls.engines = []
        cls.fake_kiosks = []
        cls.qml_warnings = []

    def test_main_qml_scene_loads_and_attaches_video_surface(self):
        engine = QQmlApplicationEngine()
        fake_kiosk = FakeKiosk()
        engine.warnings.connect(
            lambda warnings: self.__class__.qml_warnings.extend(str(warning) for warning in warnings)
        )
        engine.rootContext().setContextProperty("kiosk", fake_kiosk)
        engine.load(QUrl("qrc:/qml/KioskMain.qml"))
        roots = engine.rootObjects()
        self.assertTrue(roots, "KioskMain.qml did not load; inspect QML warnings.")
        self.assertIsNotNone(fake_kiosk._video_item, "QML did not attach the video surface.")

        # All controls use the dedicated bottom action bar, independent of the guide card.
        self.__class__.app.processEvents()
        content = roots[0].findChild(QQuickItem, "contentRoot")
        panel = roots[0].findChild(QQuickItem, "instructionPanel")
        action_bar = roots[0].findChild(QQuickItem, "actionBar")
        capture_button = roots[0].findChild(QQuickItem, "captureButton")
        save_button = roots[0].findChild(QQuickItem, "saveButton")
        retake_button = roots[0].findChild(QQuickItem, "retakeButton")
        open_folder_button = roots[0].findChild(QQuickItem, "openFolderButton")
        next_member_button = roots[0].findChild(QQuickItem, "nextMemberButton")
        for name, item in (
            ("content root", content),
            ("instruction panel", panel),
            ("action bar", action_bar),
            ("capture button", capture_button),
            ("save button", save_button),
            ("retake button", retake_button),
            ("open folder button", open_folder_button),
            ("next member button", next_member_button),
        ):
            self.assertIsNotNone(item, f"Could not find QML item: {name}")

        self.assertGreater(action_bar.height(), 0)
        bar_position = action_bar.mapToItem(content, 0, 0)
        self.assertGreaterEqual(bar_position.y(), 0)
        self.assertLessEqual(
            bar_position.y() + action_bar.height(),
            content.height() + 0.5,
            "Action bar extends outside the application content area.",
        )

        expected_visibility = {
            "live": (True, False, False, False, False),
            "review": (False, True, True, False, False),
            "saved": (False, False, False, True, True),
        }
        action_items = (
            capture_button, save_button, retake_button, open_folder_button, next_member_button
        )
        for mode, expected in expected_visibility.items():
            fake_kiosk.setMode(mode)
            self.__class__.app.processEvents()
            actual = tuple(item.isVisible() for item in action_items)
            self.assertEqual(actual, expected, f"Wrong action buttons for mode {mode}: {actual}")
            for item in action_items:
                if item.isVisible():
                    item_pos = item.mapToItem(action_bar, 0, 0)
                    self.assertGreaterEqual(item_pos.x(), 0, f"Button extends left of action bar in {mode}.")
                    self.assertGreaterEqual(item_pos.y(), 0, f"Button extends above action bar in {mode}.")
                    self.assertLessEqual(
                        item_pos.x() + item.width(),
                        action_bar.width() + 0.5,
                        f"Button extends right of action bar in {mode}.",
                    )
                    self.assertLessEqual(
                        item_pos.y() + item.height(),
                        action_bar.height() + 0.5,
                        f"Button extends below action bar in {mode}.",
                    )

        # Keep both objects alive for the test process lifetime so bindings are not evaluated
        # after the context property has gone away during deferred QObject destruction.
        self.__class__.engines.append(engine)
        self.__class__.fake_kiosks.append(fake_kiosk)
        roots[0].setVisible(False)
        problematic_warnings = [
            warning for warning in self.__class__.qml_warnings
            if "Binding loop" in warning or "TypeError" in warning
        ]
        self.assertFalse(problematic_warnings, "\\n".join(problematic_warnings))


if __name__ == "__main__":
    unittest.main()

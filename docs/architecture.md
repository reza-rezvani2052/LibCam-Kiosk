# LibCam Kiosk Architecture

## Scope and boundaries

The **libcam-kiosk** branch contains the public-facing member-photo Kiosk, not the full librarian workstation application. The full app's database, member administration, gallery builder, identity recognition, browser automation, and related dependencies are intentionally excluded. Avoid merging this branch wholesale into **develop** or **master**: its deletions are intentional. Port shared changes deliberately when needed.

The Kiosk is a PySide6 application with a Qt Quick/QML presentation layer and a Python backend. The QML file is the source of truth for the visual layout; there is no parallel QWidget form or QSS stylesheet for this interface.

## Runtime composition

### Startup sequence

1. **run_kiosk_dev.py** is the source-development entry point. It validates that both model files already exist locally and asks **build_qml_resources.py** to update the generated Qt resource module when needed. If either model is missing or incomplete, startup preparation stops with an error; no model download is attempted. It then calls **kiosk_main.main(allow_virtual_cameras=True)**.
2. **build_qml_resources.py** parses **resources/resources.qrc**, inspects the manifest and all files referenced by it, and recompiles **resources_rc.py** if the output is missing or any input is newer. This specifically includes changes to **qml/KioskMain.qml**, even when the QRC manifest itself has not changed. The release build forces this compilation.
3. **kiosk_main.py** configures rotating logging, creates **QGuiApplication** and **QQmlApplicationEngine**, registers **VideoFrameItem** as **LibCam.Kiosk 1.0**, injects the **KioskController** as the **kiosk** context property, and loads **qrc:/qml/KioskMain.qml**.
4. The root window receives the application icon from the embedded resources. After QML loads, **Component.onCompleted** attaches the **VideoFrameItem**; the controller then starts its vision worker and camera.
5. **aboutToQuit** calls the controller's shutdown method to stop the timer, release the camera and stop the vision thread.

### Presentation layer

- **qml/KioskMain.qml** defines the resizable 1220 × 790 initial window (minimum 960 × 690), RTL layout mirroring, dark navy background, status indicator, camera preview, instruction panel, action bar and confirmation dialogs.
- The instruction panel uses the dark theme (**#14243a** background and **#26374c** border) with light text and teal/blue accents. The preview card and action bar use the same navy palette; action controls vary by state.
- The QML header references **qrc:/images/app-icon.ico**. **resources/resources.qrc** embeds this icon and the QML document under the aliases **images/app-icon.ico** and **qml/KioskMain.qml**. QML rendering of the ICO format has not yet been verified in a packaged Windows run.
- QML properties bind to controller state (**isLive**, **isProcessing**, **isReview**, **isSaved**, **cameraReady**, **visionReady**, **canCapture**, **statusText** and **statusError**). The action bar switches its controls based on the current mode instead of opening a separate window for each step.

### Python backend

- **app/components/member_photo_kiosk/ui/kiosk_window.py** contains **KioskController** and **VideoFrameItem**.
- **KioskController** owns the camera adapter, controller state, output path, timers, signals/slots and clean shutdown. **statusChanged** updates messages and error state; **uiStateChanged** notifies QML about readiness and workflow transitions.
- **VideoFrameItem** is a **QQuickPaintedItem**. It converts OpenCV BGR frames to RGB and draws them with aspect-fit scaling. The live preview is mirrored; a captured crop is shown without mirroring.
- The camera timer polls at 33 ms intervals. Camera discovery and opening use the shared **app/infrastructure/camera/controller.py** adapter.
- **app/components/member_photo_kiosk/core/vision_worker.py** loads YOLO and performs inference on a background **QThread**, not the UI thread. It retains only the newest frame to avoid accumulating stale camera frames and samples pose inference at intervals of about 0.22 seconds. Inference is configured for CPU.

## Capture and state workflow

The controller exposes four modes to QML:

1. **live**: display the camera and enable manual capture only when the camera and vision models are ready.
2. **processing**: freeze the live workflow while the worker validates the capture and prepares the crop.
3. **review**: show the crop for the visitor to accept or retake it.
4. **saved**: show the saved status and actions for opening the output folder, confirming a new capture, or starting the next member.

Automatic capture is implemented in **core/gesture_detector.py** and the vision worker:

- YOLO Pose keypoints use confidence checks; either wrist can be above its corresponding shoulder, which handles the left/right ambiguity of mirrored webcam previews.
- The hand must remain raised for about 0.8 seconds to trigger. The detector then disarms and requires the hand to be lowered for about 0.5 seconds before it can trigger again.
- If multiple people are found, pose-based gesture checks use the person with the largest detected person box.
- For capture, the face detector runs on the chosen frame. If multiple faces are present, the largest detected face is used.
- **core/image_cropper.py** crops around the face with fixed padding (22% horizontally, 28% above, and 24% below), clamped to the frame bounds. These margins should be validated with the real camera, since camera framing can affect whether forehead, chin, or hands appear in the crop.
- If no usable face/crop is found, the worker reports an error and resumes the live workflow. A successful crop moves the UI to review mode.

Manual capture uses the latest available frame and schedules the request through the worker. It does not run model inference synchronously on the GUI thread.

## Output and privacy

- **KioskController._get_output_file()** uses **QStandardPaths.PicturesLocation**, falling back to the user's home Pictures directory if Qt does not provide a location, then appends **LibCam Kiosk/samanpl.jpg**.
- Saving writes a temporary file named **samanpl.tmp.jpg** and atomically replaces **samanpl.jpg** only after JPG encoding succeeds.
- Startup removes only the Kiosk-owned output and temporary files. It does not remove arbitrary files from the Pictures folder.
- If startup cleanup fails, the controller keeps capture disabled. The next-member and saved-photo retake actions ask for confirmation before deleting the current saved JPG.
- No HTTP request, browser automation or direct upload to Saman occurs.
- On Windows, logs are written to **%LOCALAPPDATA%\LibCamKiosk\logs\libcam-kiosk.log**; the rotating handler keeps up to three backups of approximately 1 MB each. If **LOCALAPPDATA** is unavailable, the fallback is **~/.local/share/LibCamKiosk/logs**.

## Model assets and packaging

Runtime model paths are defined in **app/components/member_photo_kiosk/paths.py**:

- **models/yolo/yolov8n-face-lindevs.pt**: the face detector; it is tracked using Git LFS in the source repository.
- **models/yolo/yolo26n-pose.pt**: the YOLO Pose weights supplied locally by the developer.
- **model_assets.py** validates local model files and rejects missing, undersized, or likely Git-LFS-pointer files. It performs no network access. Source runs and builds fail with a clear error if either model is absent or incomplete.

The PyInstaller build is isolated from the main application's packaging. **LibCamKiosk.spec** resolves Qt Quick imports from the active PySide6 installation's **qml** directory and adds the QML tree to the analysis data. PyInstaller's default **_internal/** layout is retained for dependencies and QML modules; models are not included in the spec's data list.

**tools/build/build_kiosk_exe.py** performs this sequence:

1. Validate both local model files; stop immediately if either is missing or incomplete. The build never downloads model weights.
2. Force regeneration of **resources_rc.py**.
3. Run PyInstaller with **LibCamKiosk.spec**.
4. Verify **dist/kiosk/LibCamKiosk/LibCamKiosk.exe** exists.
5. Copy both model files to **dist/kiosk/LibCamKiosk/models/yolo/**, next to the executable and outside **_internal/**.
6. Print build success or failure and always print elapsed time in **HH:MM:SS** format.

The Windows wrapper is **scripts/windows/build_kiosk_exe.bat**. Incomplete or Git-LFS-pointer model files are rejected before packaging.

## Tests and CI

The tests under **tests/** cover gesture keypoints and debounce timing, crop bounds, camera-name policy, model/build helpers, QML state and resource configuration. The QML check runs with the offscreen Qt platform. The GitHub Actions workflow uses Python 3.13 on Ubuntu, installs the focused test dependencies, compiles the Qt resource collection, byte-compiles the Kiosk modules, and runs **python -m unittest discover -s tests -v**.

CI does not verify the camera hardware or perform a packaged Windows run. Before deployment, test camera discovery, capture timing, face framing, saving/deletion, and the application/header icon on the target Windows system.

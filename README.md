# LibCam Kiosk

**LibCam Kiosk** is a focused Windows desktop application for preparing a member portrait on a library registration computer. It captures a face photo, lets the visitor review it, and saves a JPG for manual upload to **samanpl.ir**. It does not log in to Saman or upload files automatically.

This branch is intentionally a Kiosk-only source tree. It does not include the librarian application's database and member-management workflows, Gallery Builder, identity recognition, browser automation, or their dependencies.

## System requirements

- **Supported operating systems:** Windows 10 (64-bit) or later.
- **Windows 7 and earlier versions are not supported.** The packaged application may fail to start on these systems.

## Features

- A resizable Qt Quick/QML window with a dark navy and teal visual theme, an application-icon resource, a camera preview, an instruction/status panel, and a separate action bar.
- A live preview that preserves the camera image's aspect ratio instead of stretching it.
- Automatic photo capture when either hand is held above the shoulder for about 0.8 seconds, plus manual capture through **گرفتن عکس**.
- YOLO Pose and face detection in a background worker so model inference does not run on the GUI thread. The worker keeps the newest frame instead of building a queue of stale frames.
- A crop around the largest detected face, followed by a review step with retake and save actions.
- JPG output at the user's Pictures location under **LibCam Kiosk/samanpl.jpg**.
- A next-member flow with confirmation before deleting a previously saved image.
- Development support for virtual cameras such as ManyCam. Packaged mode filters known virtual-camera names as a practical heuristic.
- A separate PyInstaller build with Qt Quick QML imports collected under **_internal/** and the two model files copied beside the executable.

## Development setup

Run these commands from the repository root in Windows Command Prompt or PowerShell. The commands assume the project virtual environment is at **.venv**.

    git lfs pull
    .venv\Scripts\python.exe -m pip install -r requirements-kiosk.txt
    .venv\Scripts\python.exe run_kiosk_dev.py

Both model files must already be present in **models/yolo/** before running the application or building the bundle. The face detector is tracked through Git LFS, so developers cloning the repository should run **git lfs pull** when needed. The development launcher validates both files locally and stops with a clear error if either file is missing or incomplete. It never downloads model weights.

**run_kiosk_dev.py** also checks the QRC resource inputs and regenerates **resources_rc.py** when it is missing or older than a referenced source file, including **qml/KioskMain.qml**. There is normally no need to run **pyside6-rcc** manually after editing the QML UI or the QRC manifest.

The development launcher explicitly permits virtual cameras to make it easier to test the UI and capture workflow. This policy differs from the packaged default.

## Build the Windows application

Run the dedicated build script:

    scripts\windows\build_kiosk_exe.bat

The build script validates both local model files, forces a fresh Qt resource compilation, runs PyInstaller, verifies that the executable exists, and copies both model files into the completed bundle. If either model is missing or incomplete, the build stops; it never downloads model weights.

The output layout is:

    dist/LibCam-Kiosk/
        LibCam-Kiosk.exe
        _internal/             # Python/Qt dependencies and QML import modules
        models/
            yolo/
                yolov8n-face-lindevs.pt
                yolo26n-pose.pt

The model weights are deliberately copied beside the executable, not into **_internal/**. This matches the runtime paths used by the application and makes the models easy to locate. The build script prints the elapsed build duration in **HH:MM:SS** format, including when preparation or packaging fails.

Packaged mode rejects device names matching common virtual-camera markers; this is not hardware attestation. Test the actual library webcam, portrait crop, window icon, and QML header icon on the target Windows machine before deployment. The QML header currently references the ICO resource; its rendering through the packaged Qt image-format plugins has not yet been verified on Windows.

## Tests

Run the focused Kiosk tests with the project's installed dependencies:

    .venv\Scripts\python.exe -m unittest discover -s tests -v

The GitHub Actions workflow uses Python 3.13 on Ubuntu, compiles the resource collection, byte-compiles the Kiosk modules, and runs the unit and QML checks with Qt's offscreen platform. This CI workflow does not replace a final test with the target Windows webcam and packaged executable.

## Project structure

    kiosk_main.py                         # Qt/QML application entry point
    run_kiosk_dev.py                      # Model/resource preparation for source runs
    qml/KioskMain.qml                     # Source-of-truth UI
    resources/resources.qrc                # Embedded QML and icon resources
    resources_rc.py                        # Generated Python resource module (ignored by Git)
    LibCam-Kiosk.spec                      # PyInstaller configuration
    app/components/member_photo_kiosk/     # Controller, models, gesture and crop workflow
    app/infrastructure/camera/             # Camera adapter
    tools/build/build_qml_resources.py     # Timestamp-aware QRC compilation
    tools/build/build_kiosk_exe.py         # Kiosk bundle build and model deployment
    tests/                                 # Kiosk regression tests
    docs/architecture.md                   # Architecture and runtime design
    docs/kiosk.md                          # Usage, build and troubleshooting notes

## Privacy and operational notes

- The image is saved locally. The visitor or librarian must upload it to Saman manually.
- At startup the application removes only its own previous output JPG and temporary JPG. It never clears the whole Pictures folder.
- If the prior output cannot be removed, capture is disabled to avoid leaving an old member's photo available for the next visitor.
- Model inference and gesture recognition depend on the camera, framing, lighting, and CPU. Validate these on the actual deployment setup.
- Runtime logs are written to **%LOCALAPPDATA%\LibCam-Kiosk\logs\libcam-kiosk.log** on Windows, with rotation enabled.

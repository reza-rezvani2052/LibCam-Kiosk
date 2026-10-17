# LibCam Kiosk: Usage and Deployment

LibCam Kiosk prepares a member portrait for manual upload to **samanpl.ir**. It captures the image and saves a local JPG; it does not interact with the Saman website.


## Interface

The UI is defined in **qml/KioskMain.qml** and uses a dark navy background with teal/blue accents. The instruction panel beside the camera preview was changed from a white surface to a dark navy surface (**#14243a**) with a subtle border (**#26374c**). The action bar changes its controls for live capture, processing, review and saved states.

The QML header references the icon embedded as **qrc:/images/app-icon.ico**; the same resource is assigned as the application/window icon. Rendering the ICO within the QML header has not yet been confirmed in a packaged Windows run, so include that in the target-machine checks.

## Visitor workflow

1. Start the application. It opens in a normal, resizable window and reports camera/model readiness.
2. Stand in front of the allowed camera with the face near the center of the preview.
3. For automatic capture, raise either hand above the corresponding shoulder and keep it raised for about 0.8 seconds. The detector needs the hand to be lowered for about 0.5 seconds before another automatic gesture can trigger. Alternatively, use **گرفتن عکس** for manual capture.
4. The background worker checks the pose/capture request, detects faces, and crops around the largest detected face. If no usable face crop is found, the app reports an error and returns to the live camera.
5. Inspect the crop in review mode. Choose **تکرار عکس** to return to the live preview or **ذخیره تصویر** to save the JPG.
6. After saving, use **باز کردن پوشه** to locate the output. The image is saved under the current user's Pictures location at **LibCam Kiosk/samanpl.jpg**.
7. For a saved-photo retake or the next member, the app asks for confirmation before deleting the saved file. Make sure the current member's photo has already been uploaded to Saman before proceeding.

The crop has fixed margins around the detected face. Camera placement, subject distance, lighting and framing can change the result; inspect each photo before saving.

## Development run

From the project root on Windows:

    git lfs pull
    .venv\Scripts\python.exe -m pip install -r requirements-kiosk.txt
    .venv\Scripts\python.exe run_kiosk_dev.py

Both model files must already be present in **models/yolo/** before launch. Developers who clone the repository may need **git lfs pull** to fetch LFS-managed model weights. The development launcher validates both local files and fails with a clear error if either is missing or incomplete; it never downloads model weights. The launcher automatically rebuilds **resources_rc.py** when the QRC manifest or a referenced resource (including **qml/KioskMain.qml**) is newer than the generated file. There is no normal need to invoke the resource compiler by hand.

The development launcher allows virtual cameras, such as ManyCam, for testing. This setting is explicit and is not the packaged default.

## Build the standalone application

Run:

    scripts\windows\build_kiosk_exe.bat

The output directory is **dist/kiosk/LibCamKiosk/**. The bundle contains:

- **LibCamKiosk.exe**
- **_internal/** for Python/Qt dependencies and Qt Quick QML import modules.
- **models/yolo/** beside the executable, containing **yolov8n-face-lindevs.pt** and **yolo26n-pose.pt**.

The build validates both model files before packaging, refreshes compiled Qt resources, builds through **LibCamKiosk.spec**, copies the model files beside the executable, and reports total duration as **HH:MM:SS** even if the build fails. If a model is missing or incomplete, the build stops rather than downloading it. Model files intentionally stay outside **_internal/** so runtime path resolution is consistent in source and packaged runs.

## Camera policy

Development mode allows virtual cameras to support UI testing. Packaged mode filters common virtual-camera markers in device names (including names associated with ManyCam, OBS Virtual Camera, Snap Camera, DroidCam, Iriun, XSplit, Camo, EpocCam and related tools).

This is a name-based heuristic, not proof that a camera is physical. Device names that do not contain a recognized marker may still be accepted. Validate device discovery on the actual registration computer.

## Output location, privacy and logs

The output path is based on Qt's Pictures known folder, with a home-Pictures fallback, then **LibCam Kiosk/samanpl.jpg**. The app creates the directory when saving or opening it. The save uses a temporary JPG and replaces the final file only after encoding succeeds.

At startup, LibCam Kiosk removes only its own old output JPG and **samanpl.tmp.jpg**; it never clears the whole Pictures folder. If cleanup fails, capture remains disabled. The app does not upload the file or open Saman automatically.

On Windows the log file is:

    %LOCALAPPDATA%\LibCamKiosk\logs\libcam-kiosk.log

The log rotates at roughly 1 MB and retains up to three backups. Use it when investigating model loading, camera startup, inference, or save errors.

## Troubleshooting

**No camera is available**

Confirm the webcam is connected and available to Windows. In packaged mode, check the device name: a name matching a virtual-camera marker is intentionally filtered. Remember that development mode allows virtual devices but the packaged executable does not by default.

**The camera opens, but capture is disabled**

Wait for both camera and model readiness. If either required model is missing or incomplete, place the correct model file in **models/yolo/** and rerun the application. The launcher does not download model files. For an LFS-managed file in a developer checkout, use **git lfs pull** to prepare the local repository before launch.

**Automatic hand-raise capture does not trigger**

Raise either hand clearly above its shoulder and hold it steady briefly. Ensure the shoulder and wrist are visible, that there is enough light, and that no other person is dominating the camera frame. Manual capture remains available when the application is ready.

**No face is found or the crop looks wrong**

Move to the center of the frame and check focus, lighting and camera angle. The crop uses fixed face-relative margins; it is not a full ID-photo composition engine. Always review the image before saving.

**The image is missing or cannot be saved**

Use **باز کردن پوشه** after saving and confirm the Pictures folder location. If startup cannot remove the previous Kiosk image, capture is disabled intentionally; consult the log before continuing.

**The icon is missing in the QML header**

The QML header references the embedded ICO resource. That exact rendering path has not yet been confirmed in a packaged Windows run; validate it on the target machine. The same resource is also assigned as the application/window icon.

## Before deployment

Test the packaged executable on the target computer with the real library webcam. Check camera discovery, automatic and manual capture, face crop boundaries, retake/next-member confirmation, file deletion, saved output, icon display and log creation. The CI tests run on Ubuntu with Qt's offscreen platform and do not replace these hardware and Windows checks.

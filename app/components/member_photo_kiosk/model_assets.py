"""Prepare model assets required by LibCam Kiosk."""

from __future__ import annotations

import shutil
from pathlib import Path
from urllib.request import Request, urlopen

POSE_MODEL_URL = (
    "https://github.com/ultralytics/assets/releases/download/"
    "v8.4.0/yolo26n-pose.pt"
)
MINIMUM_MODEL_BYTES = 1_000_000


def ensure_pose_model(model_path: Path) -> Path:
    """Download official pose weights at source-preparation/build time only."""
    model_path = Path(model_path)
    if model_path.is_file() and model_path.stat().st_size >= MINIMUM_MODEL_BYTES:
        return model_path

    model_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = model_path.with_suffix(model_path.suffix + ".download")
    request = Request(
        POSE_MODEL_URL,
        headers={"User-Agent": "LibCam-Kiosk-model-setup"},
    )

    try:
        with urlopen(request, timeout=60) as response:
            with temporary_path.open("wb") as destination:
                shutil.copyfileobj(response, destination)

        if temporary_path.stat().st_size < MINIMUM_MODEL_BYTES:
            raise RuntimeError(
                "The downloaded pose model is unexpectedly small; "
                "the download may have returned an error page."
            )

        temporary_path.replace(model_path)
        return model_path
    except Exception as exc:  # noqa: BLE001
        temporary_path.unlink(missing_ok=True)
        raise RuntimeError(
            "Could not prepare the YOLO pose model. Check the network connection "
            "or download the official model and place it at:\n"
            f"{model_path}\nSource: {POSE_MODEL_URL}\nDetails: {exc}"
        ) from exc

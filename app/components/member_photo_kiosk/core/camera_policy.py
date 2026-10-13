"""Policy helpers for choosing webcam devices in LibCam Kiosk."""

from __future__ import annotations


VIRTUAL_CAMERA_MARKERS = (
    "virtual",
    "manycam",
    "obs camera",
    "obs virtual",
    "snap camera",
    "snapcam",
    "droidcam",
    "iriun",
    "xsplit",
    "splitcam",
    "mmhmm",
    "camo camera",
    "epoccam",
    "ndi video",
    "youcam",
    "vcam",
)


def is_virtual_camera_name(name: str) -> bool:
    """Return True when a device name identifies a known virtual-camera source."""
    normalized = " ".join(name.casefold().split())
    return any(marker in normalized for marker in VIRTUAL_CAMERA_MARKERS)


def is_camera_allowed(name: str, *, allow_virtual_cameras: bool = False) -> bool:
    """Allow virtual camera devices only when the caller explicitly enables them."""
    return allow_virtual_cameras or not is_virtual_camera_name(name)

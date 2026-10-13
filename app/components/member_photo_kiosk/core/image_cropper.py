"""Face-crop helpers used to prepare the image uploaded to Saman."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np


def crop_detected_face(
    frame: np.ndarray,
    box: Sequence[float],
    *,
    horizontal_padding: float = 0.22,
    top_padding: float = 0.28,
    bottom_padding: float = 0.24,
) -> np.ndarray | None:
    """Crop a detected face with modest margins while keeping it inside the frame."""
    if frame is None or frame.size == 0 or len(box) < 4:
        return None

    frame_height, frame_width = frame.shape[:2]
    x1, y1, x2, y2 = (float(value) for value in box[:4])
    x1 = max(0.0, min(x1, float(frame_width)))
    x2 = max(0.0, min(x2, float(frame_width)))
    y1 = max(0.0, min(y1, float(frame_height)))
    y2 = max(0.0, min(y2, float(frame_height)))
    face_width = x2 - x1
    face_height = y2 - y1
    if face_width < 2 or face_height < 2:
        return None

    left = max(0, math.floor(x1 - face_width * horizontal_padding))
    right = min(frame_width, math.ceil(x2 + face_width * horizontal_padding))
    top = max(0, math.floor(y1 - face_height * top_padding))
    bottom = min(frame_height, math.ceil(y2 + face_height * bottom_padding))
    if right <= left or bottom <= top:
        return None

    crop = frame[top:bottom, left:right]
    if crop.size == 0:
        return None
    return crop.copy()

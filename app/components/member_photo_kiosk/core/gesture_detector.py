"""Reliable raised-hand detection for mirrored and non-mirrored webcam feeds."""

from __future__ import annotations

# COCO 17-keypoint indices used by Ultralytics Pose.
LEFT_SHOULDER_INDEX = 5
RIGHT_SHOULDER_INDEX = 6
LEFT_WRIST_INDEX = 9
RIGHT_WRIST_INDEX = 10


def _is_wrist_above_shoulder(
    keypoints: list[list[float]] | tuple[tuple[float, ...], ...],
    frame_height: int,
    shoulder_index: int,
    wrist_index: int,
    *,
    confidence_threshold: float,
    shoulder_gap_ratio: float,
) -> bool:
    """Check one wrist/shoulder pair from a COCO pose result."""
    if frame_height <= 0 or len(keypoints) <= max(shoulder_index, wrist_index):
        return False

    shoulder = keypoints[shoulder_index]
    wrist = keypoints[wrist_index]
    if len(shoulder) < 3 or len(wrist) < 3:
        return False

    shoulder_y, shoulder_confidence = shoulder[1], shoulder[2]
    wrist_y, wrist_confidence = wrist[1], wrist[2]
    if (
        shoulder_confidence < confidence_threshold
        or wrist_confidence < confidence_threshold
    ):
        return False

    minimum_gap = max(8.0, frame_height * shoulder_gap_ratio)
    return wrist_y <= shoulder_y - minimum_gap


def is_left_hand_raised(
    keypoints: list[list[float]] | tuple[tuple[float, ...], ...],
    frame_height: int,
    *,
    confidence_threshold: float = 0.25,
    shoulder_gap_ratio: float = 0.02,
) -> bool:
    """Return True when the left wrist is confidently above its shoulder."""
    return _is_wrist_above_shoulder(
        keypoints,
        frame_height,
        LEFT_SHOULDER_INDEX,
        LEFT_WRIST_INDEX,
        confidence_threshold=confidence_threshold,
        shoulder_gap_ratio=shoulder_gap_ratio,
    )


def is_right_hand_raised(
    keypoints: list[list[float]] | tuple[tuple[float, ...], ...],
    frame_height: int,
    *,
    confidence_threshold: float = 0.25,
    shoulder_gap_ratio: float = 0.02,
) -> bool:
    """Return True when the right wrist is confidently above its shoulder."""
    return _is_wrist_above_shoulder(
        keypoints,
        frame_height,
        RIGHT_SHOULDER_INDEX,
        RIGHT_WRIST_INDEX,
        confidence_threshold=confidence_threshold,
        shoulder_gap_ratio=shoulder_gap_ratio,
    )


def is_hand_raised(
    keypoints: list[list[float]] | tuple[tuple[float, ...], ...],
    frame_height: int,
    *,
    confidence_threshold: float = 0.25,
    shoulder_gap_ratio: float = 0.02,
) -> bool:
    """Accept either raised hand to tolerate left/right ambiguity in mirrored feeds."""
    return is_left_hand_raised(
        keypoints,
        frame_height,
        confidence_threshold=confidence_threshold,
        shoulder_gap_ratio=shoulder_gap_ratio,
    ) or is_right_hand_raised(
        keypoints,
        frame_height,
        confidence_threshold=confidence_threshold,
        shoulder_gap_ratio=shoulder_gap_ratio,
    )


class HandRaiseDetector:
    """Require a stable raised hand and a neutral interval before re-arming."""

    def __init__(
        self,
        *,
        confirmation_seconds: float = 0.8,
        release_seconds: float = 0.5,
    ) -> None:
        self.confirmation_seconds = confirmation_seconds
        self.release_seconds = release_seconds
        self._raised_since: float | None = None
        self._lowered_since: float | None = None
        self._armed = True

    def update(self, raised: bool, now: float) -> bool:
        """Return True once for a sustained raise; otherwise return False."""
        if raised:
            self._lowered_since = None
            if not self._armed:
                return False
            if self._raised_since is None:
                self._raised_since = now
                return False
            if now - self._raised_since >= self.confirmation_seconds:
                self._armed = False
                self._raised_since = None
                return True
            return False

        self._raised_since = None
        if self._armed:
            self._lowered_since = None
            return False

        if self._lowered_since is None:
            self._lowered_since = now
        elif now - self._lowered_since >= self.release_seconds:
            self._armed = True
            self._lowered_since = None
        return False

    def disarm(self) -> None:
        """Prevent an immediate repeated capture until the hand is lowered."""
        self._armed = False
        self._raised_since = None
        self._lowered_since = None

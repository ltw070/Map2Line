"""색상 분리 모듈 — BGR 이미지에서 붉은/푸른 레이어 마스크를 분리한다."""
import cv2
import numpy as np

# -------------------------------------------------------------------
# HSV 범위 상수 (OpenCV 기준: Hue 0-179, Saturation 0-255, Value 0-255)
# 붉은색은 Hue 0-10° (저각도) 와 160-180° (고각도) 두 범위를 OR 합산
# -------------------------------------------------------------------
_RED_LOWER1 = np.array([0, 50, 50])     # Hue 0°-10°
_RED_UPPER1 = np.array([10, 255, 255])
_RED_LOWER2 = np.array([160, 50, 50])   # Hue 160°-180°
_RED_UPPER2 = np.array([180, 255, 255])
_BLUE_LOWER = np.array([100, 50, 50])   # Hue 100°-130°
_BLUE_UPPER = np.array([130, 255, 255])

# 3x3 타원형 커널 — 인접 픽셀 갭 메우기 (MORPH_CLOSE)
_MORPH_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))


def _apply_morph_close(mask: np.ndarray) -> np.ndarray:
    """MORPH_CLOSE 로 인접 픽셀 갭을 메운다. 단독 픽셀은 제거하지 않는다."""
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, _MORPH_KERNEL)


def segment_colors(image: np.ndarray) -> dict:
    """BGR 이미지에서 붉은/푸른 레이어 마스크를 분리한다.

    붉은색: HSV Hue (0°–10°) ∪ (160°–180°) 두 범위 OR 합산.
    푸른색: HSV Hue (100°–130°).
    모폴로지: MORPH_CLOSE 로 인접 갭 메우기.
    (MORPH_OPEN 미사용 — 저해상도 도면의 단독 픽셀 앵커 보존)

    Args:
        image: BGR 형식의 numpy ndarray (H x W x 3, dtype=uint8).

    Returns:
        {"red": mask, "blue": mask} — 각 마스크는 (H x W) uint8 배열,
        탐지된 픽셀 255, 배경 0.
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    red_mask = cv2.bitwise_or(
        cv2.inRange(hsv, _RED_LOWER1, _RED_UPPER1),
        cv2.inRange(hsv, _RED_LOWER2, _RED_UPPER2),
    )
    blue_mask = cv2.inRange(hsv, _BLUE_LOWER, _BLUE_UPPER)

    return {
        "red": _apply_morph_close(red_mask),
        "blue": _apply_morph_close(blue_mask),
    }

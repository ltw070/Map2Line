"""앵커 포인트 탐지 모듈 — 붉은 레이어 마스크에서 기둥 중심 좌표를 추출한다."""
import cv2
import numpy as np

# -------------------------------------------------------------------
# 면적 필터 임계값
#
# _MIN_AREA_FRAC: 이미지 전체 픽셀 수 대비 최소 Blob 면적 비율
#   - 100x100 이미지 → rel = 50 → capped to _MAX_MIN_AREA(14) → min_area=14
#   - 30% 축소 36x36 이미지 → rel = 6 → capped to max(_ABS_MIN_AREA,6) = 6
#     (스케일 불변: 30% 축소 r=6 → r≈2 → area≈11 >= 6 → 탐지 성공)
#
# _MAX_MIN_AREA: min_area 의 상한. r=2 노이즈(area=13) 를 제거하면서
#   실제 도면 소형 앵커(area=14)를 탐지할 수 있는 경계값.
#
# _ABS_MIN_AREA: 절대 하한 (극소 이미지·비율 계산 방어)
# _ABS_MAX_AREA: 절대 상한 (텍스트 뭉침 등 거대 노이즈 제거)
# -------------------------------------------------------------------
_MIN_AREA_FRAC = 0.005
_MAX_MIN_AREA = 14
_ABS_MIN_AREA = 5
_ABS_MAX_AREA = 5000


def detect_anchors(red_mask: np.ndarray) -> list:
    """붉은 레이어 마스크에서 기둥 중심 좌표 목록을 반환한다.

    연결 컴포넌트 분석(connectedComponentsWithStats)으로 각 Blob 면적을 측정하고
    이미지 크기 대비 상대 임계값을 동적으로 계산하여 앵커를 채택한다.

    동적 min_area = max(_ABS_MIN_AREA, min(_MAX_MIN_AREA, H*W*_MIN_AREA_FRAC))

    이 방식은 아래 조건을 동시에 만족한다:
    - 단독 픽셀 노이즈(r=1, area=5) 및 소형 노이즈(r=2, area=13) 제거
    - 30% 이상 축소 이미지에서 r=6 → r≈2(area≈11) 탐지 유지
    - 실제 도면의 소형 앵커(area≈14) 탐지 유지

    Args:
        red_mask: 붉은 색상 마스크 (H x W, dtype=uint8). 탐지 픽셀 255, 배경 0.

    Returns:
        앵커 중심 좌표 목록 [(x1, y1), (x2, y2), ...]. 빈 마스크이면 [].
    """
    h, w = red_mask.shape[:2]
    total_pixels = h * w
    min_area = max(_ABS_MIN_AREA, min(_MAX_MIN_AREA, int(total_pixels * _MIN_AREA_FRAC)))

    num_labels, _, stats, centroids = cv2.connectedComponentsWithStats(
        red_mask, connectivity=8
    )
    anchors = []
    for i in range(1, num_labels):  # 레이블 0은 배경
        area = stats[i, cv2.CC_STAT_AREA]
        if min_area <= area <= _ABS_MAX_AREA:
            cx = int(round(centroids[i][0]))
            cy = int(round(centroids[i][1]))
            anchors.append((cx, cy))
    return anchors

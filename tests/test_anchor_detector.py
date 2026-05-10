"""앵커 포인트 탐지 모듈 테스트 — Task 1-3."""
import numpy as np
import pytest
import cv2
from src.preprocessing.anchor_detector import detect_anchors


@pytest.fixture
def single_blob_mask():
    """중심 (50, 50), 반지름 8px의 단일 원형 Blob 마스크."""
    mask = np.zeros((100, 100), dtype=np.uint8)
    cv2.circle(mask, (50, 50), 8, 255, -1)
    return mask


@pytest.fixture
def multi_blob_mask():
    """세 개의 원형 Blob: (20,20), (60,40), (80,70) 각 r=6."""
    mask = np.zeros((120, 120), dtype=np.uint8)
    for cx, cy in [(20, 20), (60, 40), (80, 70)]:
        cv2.circle(mask, (cx, cy), 6, 255, -1)
    return mask


@pytest.fixture
def noise_blob_mask():
    """유효 Blob 1개 (r=8) + 노이즈 점 2개 (r=1, r=2)."""
    mask = np.zeros((100, 100), dtype=np.uint8)
    cv2.circle(mask, (50, 50), 8, 255, -1)   # 유효
    cv2.circle(mask, (10, 10), 1, 255, -1)   # 노이즈
    cv2.circle(mask, (90, 90), 2, 255, -1)   # 노이즈
    return mask


class TestDetectAnchors:
    def test_returns_list(self, single_blob_mask):
        result = detect_anchors(single_blob_mask)
        assert isinstance(result, list)

    def test_single_blob_detected(self, single_blob_mask):
        result = detect_anchors(single_blob_mask)
        assert len(result) == 1

    def test_single_blob_coordinates(self, single_blob_mask):
        """좌표가 실제 중심(50,50)에서 ±3px 이내."""
        result = detect_anchors(single_blob_mask)
        x, y = result[0]
        assert abs(x - 50) <= 3
        assert abs(y - 50) <= 3

    def test_coordinate_type_is_int(self, single_blob_mask):
        result = detect_anchors(single_blob_mask)
        x, y = result[0]
        assert isinstance(x, int)
        assert isinstance(y, int)

    def test_multiple_blobs_detected(self, multi_blob_mask):
        result = detect_anchors(multi_blob_mask)
        assert len(result) == 3

    def test_noise_filtered_out(self, noise_blob_mask):
        """노이즈 픽셀은 필터링되어 유효 Blob 1개만 반환."""
        result = detect_anchors(noise_blob_mask)
        assert len(result) == 1

    def test_empty_mask_returns_empty(self):
        mask = np.zeros((100, 100), dtype=np.uint8)
        result = detect_anchors(mask)
        assert result == []

    def test_scale_30pct_still_detects(self, multi_blob_mask):
        """30% 축소 마스크에서도 Blob 탐지 (최소 2개 이상)."""
        small = cv2.resize(multi_blob_mask, None, fx=0.3, fy=0.3,
                           interpolation=cv2.INTER_NEAREST)
        result = detect_anchors(small)
        assert len(result) >= 2, f"30% 축소에서 2개 이상 탐지 필요, 실제: {len(result)}"

    def test_real_map_detects_anchors(self, map_sample_bgr):
        """실제 도면에서 붉은 기둥 1개 이상 탐지."""
        if map_sample_bgr is None:
            pytest.skip("ref_map/map_sample.png 없음")
        from src.preprocessing.color_segmentation import segment_colors
        red_mask = segment_colors(map_sample_bgr)["red"]
        result = detect_anchors(red_mask)
        assert len(result) >= 1, "실제 도면에서 앵커가 탐지되어야 한다"

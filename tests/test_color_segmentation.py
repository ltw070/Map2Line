"""Task 1-2: 색상 분리 모듈 테스트 (Red → Green → Refactor)."""
import numpy as np
import pytest
import cv2
from src.preprocessing.color_segmentation import segment_colors


class TestSegmentColors:
    def test_return_keys(self, white_bgr_image):
        result = segment_colors(white_bgr_image)
        assert "red" in result
        assert "blue" in result

    def test_red_mask_detected(self, red_dot_image):
        result = segment_colors(red_dot_image)
        assert result["red"].sum() > 0, "붉은 픽셀이 탐지되어야 한다"

    def test_blue_mask_detected(self):
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        # BGR (200, 120, 30) → HSV 약 110°, 85%, 78% → 푸른색 범위
        cv2.circle(img, (50, 50), 15, (200, 120, 30), -1)
        result = segment_colors(img)
        assert result["blue"].sum() > 0, "푸른 픽셀이 탐지되어야 한다"

    def test_white_image_no_detection(self, white_bgr_image):
        result = segment_colors(white_bgr_image)
        assert result["red"].sum() == 0
        assert result["blue"].sum() == 0

    def test_mask_shape_matches_input(self, red_dot_image):
        result = segment_colors(red_dot_image)
        h, w = red_dot_image.shape[:2]
        assert result["red"].shape == (h, w)
        assert result["blue"].shape == (h, w)

    def test_mask_dtype_is_uint8(self, red_dot_image):
        result = segment_colors(red_dot_image)
        assert result["red"].dtype == np.uint8
        assert result["blue"].dtype == np.uint8

    def test_illumination_reduced_still_detects_red(self):
        """밝기 -20% 에서도 붉은 픽셀 탐지"""
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        cv2.circle(img, (50, 50), 15, (0, 0, 200), -1)
        dark = (img * 0.8).astype(np.uint8)
        result = segment_colors(dark)
        assert result["red"].sum() > 0

    def test_illumination_bright_still_detects_red(self):
        """밝기 +20% (클리핑) 에서도 붉은 픽셀 탐지"""
        img = np.ones((100, 100, 3), dtype=np.uint8) * 200
        cv2.circle(img, (50, 50), 15, (0, 0, 220), -1)
        bright = np.clip(img.astype(np.int32) * 1.2, 0, 255).astype(np.uint8)
        result = segment_colors(bright)
        assert result["red"].sum() > 0

    def test_red_recall_on_real_map(self, map_sample_bgr):
        """실제 도면에서 붉은 기둥이 1개 이상 탐지"""
        if map_sample_bgr is None:
            pytest.skip("ref_map/map_sample.png 없음")
        result = segment_colors(map_sample_bgr)
        assert result["red"].sum() > 0, "실제 도면에서 붉은 픽셀이 탐지되어야 한다"

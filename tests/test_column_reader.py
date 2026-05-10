"""Task 2-3 OCR 교차검증 테스트 (Red 단계).

column_reader.verify_with_ocr() 함수의 계약을 검증한다:
  1. 반환 형식 — 필수 키 존재, 타입 일치
  2. 해상도 충분 + OCR 일치 → 신뢰도 +0.05 boost
  3. 해상도 충분 + OCR 불일치 → 신뢰도 -0.10 penalty
  4. 저해상도 → 예외 없이 신뢰도 현상 유지
  5. EasyOCR 미설치(mock) → 예외 없이 신뢰도 현상 유지
  6. confidence 클리핑 (0.0~1.0)
  7. ocr_text 키 항상 반환
  8. 원본 fine_result 딕셔너리 변경 없음 (side-effect 금지)
"""
from __future__ import annotations

import copy
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.ocr.column_reader import verify_with_ocr

# ---------------------------------------------------------------------------
# 공용 fixture
# ---------------------------------------------------------------------------

HIGH_RES_W = 600   # MIN_WIDTH_PX(400) 이상 — OCR 시도
LOW_RES_W = 200    # MIN_WIDTH_PX(400) 미만 — OCR skip


def _make_image(width: int, height: int = 300) -> np.ndarray:
    """합성 BGR 이미지를 반환한다."""
    return np.ones((height, width, 3), dtype=np.uint8) * 200


def _fine_result(line: str = "Line_A", confidence: float = 0.80) -> Dict[str, Any]:
    return {
        "line": line,
        "section": "0",
        "confidence": confidence,
        "inference_time_ms": 0.5,
    }


# ---------------------------------------------------------------------------
# 1. 반환 형식 검증
# ---------------------------------------------------------------------------

class TestReturnFormat:
    """verify_with_ocr 반환 딕셔너리의 필수 키와 타입을 검증한다."""

    def test_required_keys_present(self):
        """반환값에 5개 필수 키가 모두 존재해야 한다."""
        img = _make_image(HIGH_RES_W)
        result = verify_with_ocr(img, _fine_result())
        required = {"line", "section", "confidence", "inference_time_ms", "ocr_text"}
        assert required.issubset(result.keys()), f"누락 키: {required - result.keys()}"

    def test_confidence_is_float_in_range(self):
        """confidence는 float이며 0.0~1.0 범위여야 한다."""
        img = _make_image(HIGH_RES_W)
        result = verify_with_ocr(img, _fine_result())
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_ocr_text_is_str(self):
        """ocr_text는 str 타입이어야 한다."""
        img = _make_image(LOW_RES_W)
        result = verify_with_ocr(img, _fine_result())
        assert isinstance(result["ocr_text"], str)

    def test_line_and_section_are_str(self):
        """line, section 필드는 str 타입이어야 한다."""
        img = _make_image(HIGH_RES_W)
        result = verify_with_ocr(img, _fine_result())
        assert isinstance(result["line"], str)
        assert isinstance(result["section"], str)

    def test_inference_time_ms_is_float(self):
        """inference_time_ms는 float 타입이어야 한다."""
        img = _make_image(HIGH_RES_W)
        result = verify_with_ocr(img, _fine_result())
        assert isinstance(result["inference_time_ms"], float)


# ---------------------------------------------------------------------------
# 2. 저해상도 graceful skip
# ---------------------------------------------------------------------------

class TestLowResolution:
    """저해상도 이미지에서는 OCR을 시도하지 않고 신뢰도를 유지해야 한다."""

    def test_low_res_no_exception(self):
        """저해상도 이미지에서 예외가 발생하지 않아야 한다."""
        img = _make_image(LOW_RES_W)
        result = verify_with_ocr(img, _fine_result(confidence=0.75))
        assert result is not None

    def test_low_res_confidence_unchanged(self):
        """저해상도 이미지에서 신뢰도가 변경되지 않아야 한다."""
        original_conf = 0.75
        img = _make_image(LOW_RES_W)
        result = verify_with_ocr(img, _fine_result(confidence=original_conf))
        assert result["confidence"] == pytest.approx(original_conf, abs=1e-6)

    def test_low_res_ocr_text_empty(self):
        """저해상도 이미지에서 ocr_text는 빈 문자열이어야 한다."""
        img = _make_image(LOW_RES_W)
        result = verify_with_ocr(img, _fine_result())
        assert result["ocr_text"] == ""

    @pytest.mark.parametrize("width", [1, 50, 100, 399])
    def test_various_low_res_widths(self, width: int):
        """MIN_WIDTH_PX(400) 미만의 다양한 너비에서 신뢰도가 유지된다."""
        original_conf = 0.80
        img = _make_image(width)
        result = verify_with_ocr(img, _fine_result(confidence=original_conf))
        assert result["confidence"] == pytest.approx(original_conf, abs=1e-6)


# ---------------------------------------------------------------------------
# 3. OCR 일치 → 신뢰도 boost
# ---------------------------------------------------------------------------

class TestOcrMatch:
    """OCR이 line 이름을 포함하는 텍스트를 추출하면 신뢰도가 +0.05 상승해야 한다."""

    def test_ocr_match_boosts_confidence(self):
        """OCR 일치 시 신뢰도가 OCR_MATCH_BOOST(0.05)만큼 상승해야 한다."""
        original_conf = 0.80
        img = _make_image(HIGH_RES_W)
        fine = _fine_result(line="Line_A", confidence=original_conf)

        # _EASYOCR_AVAILABLE=True + _ocr_read_text mock으로 "Line_A" 포함 텍스트 반환
        with patch("src.ocr.column_reader._EASYOCR_AVAILABLE", True), \
             patch("src.ocr.column_reader._ocr_read_text", return_value="Line_A 102"):
            result = verify_with_ocr(img, fine)

        expected = original_conf + 0.05
        assert result["confidence"] == pytest.approx(expected, abs=1e-6)

    def test_ocr_match_updates_section(self):
        """OCR 일치 시 3자리 기둥 번호가 section에 반영되어야 한다."""
        img = _make_image(HIGH_RES_W)
        fine = _fine_result(line="Line_A", confidence=0.80)

        with patch("src.ocr.column_reader._EASYOCR_AVAILABLE", True), \
             patch("src.ocr.column_reader._ocr_read_text", return_value="Line_A 102"):
            result = verify_with_ocr(img, fine)

        assert result["section"] == "102"

    def test_ocr_match_saves_raw_text(self):
        """OCR 원본 텍스트가 ocr_text 키에 저장되어야 한다."""
        img = _make_image(HIGH_RES_W)
        fine = _fine_result(line="Line_A", confidence=0.80)
        raw_text = "Line_A 102"

        with patch("src.ocr.column_reader._EASYOCR_AVAILABLE", True), \
             patch("src.ocr.column_reader._ocr_read_text", return_value=raw_text):
            result = verify_with_ocr(img, fine)

        assert result["ocr_text"] == raw_text

    def test_confidence_clamped_to_1_0_on_boost(self):
        """boost 후 신뢰도가 1.0을 초과하지 않아야 한다."""
        img = _make_image(HIGH_RES_W)
        fine = _fine_result(line="Line_A", confidence=0.98)

        with patch("src.ocr.column_reader._EASYOCR_AVAILABLE", True), \
             patch("src.ocr.column_reader._ocr_read_text", return_value="Line_A 102"):
            result = verify_with_ocr(img, fine)

        assert result["confidence"] <= 1.0


# ---------------------------------------------------------------------------
# 4. OCR 불일치 → 신뢰도 penalty
# ---------------------------------------------------------------------------

class TestOcrMismatch:
    """OCR이 line 이름을 포함하지 않는 텍스트를 반환하면 신뢰도가 -0.10 하락해야 한다."""

    def test_ocr_mismatch_penalizes_confidence(self):
        """OCR 불일치 시 신뢰도가 OCR_MISMATCH_PENALTY(0.10)만큼 하락해야 한다."""
        original_conf = 0.80
        img = _make_image(HIGH_RES_W)
        fine = _fine_result(line="Line_A", confidence=original_conf)

        # OCR이 Line_A를 포함하지 않는 텍스트를 반환
        with patch("src.ocr.column_reader._EASYOCR_AVAILABLE", True), \
             patch("src.ocr.column_reader._ocr_read_text", return_value="Line_B 205"):
            result = verify_with_ocr(img, fine)

        expected = original_conf - 0.10
        assert result["confidence"] == pytest.approx(expected, abs=1e-6)

    def test_ocr_mismatch_section_unchanged(self):
        """OCR 불일치 시 section이 원본 fine_result 값을 유지해야 한다."""
        img = _make_image(HIGH_RES_W)
        fine = _fine_result(line="Line_A", confidence=0.80)

        with patch("src.ocr.column_reader._EASYOCR_AVAILABLE", True), \
             patch("src.ocr.column_reader._ocr_read_text", return_value="Line_B 205"):
            result = verify_with_ocr(img, fine)

        assert result["section"] == fine["section"]

    def test_confidence_clamped_to_0_0_on_penalty(self):
        """penalty 후 신뢰도가 0.0 미만으로 내려가지 않아야 한다."""
        img = _make_image(HIGH_RES_W)
        fine = _fine_result(line="Line_A", confidence=0.05)

        with patch("src.ocr.column_reader._EASYOCR_AVAILABLE", True), \
             patch("src.ocr.column_reader._ocr_read_text", return_value="Line_B 205"):
            result = verify_with_ocr(img, fine)

        assert result["confidence"] >= 0.0

    def test_ocr_empty_text_treated_as_skip(self):
        """OCR이 빈 문자열을 반환하면 신뢰도 현상 유지 (불일치 penalty 없음)."""
        original_conf = 0.80
        img = _make_image(HIGH_RES_W)
        fine = _fine_result(line="Line_A", confidence=original_conf)

        with patch("src.ocr.column_reader._EASYOCR_AVAILABLE", True), \
             patch("src.ocr.column_reader._ocr_read_text", return_value=""):
            result = verify_with_ocr(img, fine)

        assert result["confidence"] == pytest.approx(original_conf, abs=1e-6)


# ---------------------------------------------------------------------------
# 5. EasyOCR 미설치 → graceful degrade
# ---------------------------------------------------------------------------

class TestEasyOcrNotInstalled:
    """easyocr 패키지가 없을 때 예외 없이 신뢰도를 유지해야 한다."""

    def test_easyocr_not_installed_no_exception(self):
        """_EASYOCR_AVAILABLE=False일 때 예외가 발생하지 않아야 한다."""
        img = _make_image(HIGH_RES_W)
        fine = _fine_result(confidence=0.75)

        with patch("src.ocr.column_reader._EASYOCR_AVAILABLE", False):
            result = verify_with_ocr(img, fine)

        assert result is not None

    def test_easyocr_not_installed_confidence_unchanged(self):
        """_EASYOCR_AVAILABLE=False일 때 신뢰도가 변경되지 않아야 한다."""
        original_conf = 0.75
        img = _make_image(HIGH_RES_W)
        fine = _fine_result(confidence=original_conf)

        with patch("src.ocr.column_reader._EASYOCR_AVAILABLE", False):
            result = verify_with_ocr(img, fine)

        assert result["confidence"] == pytest.approx(original_conf, abs=1e-6)


# ---------------------------------------------------------------------------
# 6. 원본 딕셔너리 불변성 (side-effect 금지)
# ---------------------------------------------------------------------------

class TestSideEffectFree:
    """verify_with_ocr는 입력 fine_result를 수정하지 않아야 한다."""

    def test_fine_result_not_mutated_on_match(self):
        """OCR 일치 시에도 원본 fine_result가 변경되지 않아야 한다."""
        img = _make_image(HIGH_RES_W)
        fine = _fine_result(line="Line_A", confidence=0.80)
        original = copy.deepcopy(fine)

        with patch("src.ocr.column_reader._EASYOCR_AVAILABLE", True), \
             patch("src.ocr.column_reader._ocr_read_text", return_value="Line_A 102"):
            verify_with_ocr(img, fine)

        assert fine == original

    def test_fine_result_not_mutated_on_mismatch(self):
        """OCR 불일치 시에도 원본 fine_result가 변경되지 않아야 한다."""
        img = _make_image(HIGH_RES_W)
        fine = _fine_result(line="Line_A", confidence=0.80)
        original = copy.deepcopy(fine)

        with patch("src.ocr.column_reader._EASYOCR_AVAILABLE", True), \
             patch("src.ocr.column_reader._ocr_read_text", return_value="Line_B 205"):
            verify_with_ocr(img, fine)

        assert fine == original


# ---------------------------------------------------------------------------
# 7. 성능 테스트 (저해상도 skip 기준)
# ---------------------------------------------------------------------------

class TestPerformance:
    """저해상도 skip 경로는 1ms 미만이어야 한다 (OCR 추론 없이 즉시 반환)."""

    def test_low_res_returns_quickly(self):
        """저해상도 경로에서 10ms 이내에 반환해야 한다."""
        import time
        img = _make_image(LOW_RES_W)
        fine = _fine_result()

        start = time.perf_counter()
        verify_with_ocr(img, fine)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        assert elapsed_ms < 10.0, f"저해상도 skip 경로가 너무 느림: {elapsed_ms:.1f}ms"

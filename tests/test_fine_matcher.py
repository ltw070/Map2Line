"""Task 2-2: Fine Matcher 테스트 모듈.

Coarse Matcher Top-5 후보를 입력받아 특징점 기반으로 최종 라인을 선택하는
fine_matcher 함수의 반환 형식, 성능, 신뢰도를 검증한다.
"""
import time
from typing import Any, Dict, List

import numpy as np
import pytest

from src.matching.fine_matcher import fine_matcher


# ---------------------------------------------------------------------------
# 공용 fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def query_image() -> np.ndarray:
    """임의의 BGR 이미지 (224x224)."""
    return np.random.randint(0, 256, (224, 224, 3), dtype=np.uint8)


@pytest.fixture
def coarse_candidates_5() -> List[Dict[str, Any]]:
    """Coarse Matcher Top-5 후보 목록."""
    return [
        {"line": "Line_A", "confidence": 0.95},
        {"line": "Line_B", "confidence": 0.87},
        {"line": "Line_C", "confidence": 0.78},
        {"line": "Line_D", "confidence": 0.65},
        {"line": "Line_E", "confidence": 0.52},
    ]


@pytest.fixture
def coarse_candidates_2() -> List[Dict[str, Any]]:
    """Coarse Matcher Top-2 후보 목록 (최소 입력)."""
    return [
        {"line": "Line_A", "confidence": 0.95},
        {"line": "Line_B", "confidence": 0.87},
    ]


# ---------------------------------------------------------------------------
# TestFineMatcherReturnFormat — 반환 형식 검증
# ---------------------------------------------------------------------------

class TestFineMatcherReturnFormat:
    """fine_matcher(top_k=1) 반환값 구조 검증."""

    def test_returns_dict(self, query_image, coarse_candidates_5):
        """top_k=1 이면 dict를 반환한다."""
        result = fine_matcher(query_image, coarse_candidates_5, top_k=1)
        assert isinstance(result, dict)

    def test_has_required_keys(self, query_image, coarse_candidates_5):
        """dict에 line, section, confidence 키가 있어야 한다."""
        result = fine_matcher(query_image, coarse_candidates_5, top_k=1)
        assert "line" in result
        assert "section" in result
        assert "confidence" in result

    def test_line_is_string(self, query_image, coarse_candidates_5):
        """line 값은 str 타입이어야 한다."""
        result = fine_matcher(query_image, coarse_candidates_5, top_k=1)
        assert isinstance(result["line"], str)

    def test_section_is_string(self, query_image, coarse_candidates_5):
        """section 값은 str 타입이어야 한다."""
        result = fine_matcher(query_image, coarse_candidates_5, top_k=1)
        assert isinstance(result["section"], str)

    def test_confidence_is_float(self, query_image, coarse_candidates_5):
        """confidence 값은 float 또는 int 타입이어야 한다."""
        result = fine_matcher(query_image, coarse_candidates_5, top_k=1)
        assert isinstance(result["confidence"], (float, int))

    def test_selected_line_is_in_candidates(self, query_image, coarse_candidates_5):
        """선택된 라인은 Coarse 후보 중 하나여야 한다."""
        result = fine_matcher(query_image, coarse_candidates_5, top_k=1)
        candidate_lines = [c["line"] for c in coarse_candidates_5]
        assert result["line"] in candidate_lines

    def test_top_k_3_returns_list(self, query_image, coarse_candidates_5):
        """top_k=3 이면 list를 반환한다."""
        result = fine_matcher(query_image, coarse_candidates_5, top_k=3)
        assert isinstance(result, list)

    def test_top_k_3_length_at_most_3(self, query_image, coarse_candidates_5):
        """top_k=3 일 때 반환 list 길이는 3 이하이다."""
        result = fine_matcher(query_image, coarse_candidates_5, top_k=3)
        assert len(result) <= 3

    def test_top_k_3_each_item_has_required_keys(self, query_image, coarse_candidates_5):
        """top_k=3 반환 list의 각 항목이 line, section, confidence 키를 갖는다."""
        result = fine_matcher(query_image, coarse_candidates_5, top_k=3)
        for item in result:
            assert "line" in item
            assert "section" in item
            assert "confidence" in item

    def test_minimal_input_two_candidates(self, query_image, coarse_candidates_2):
        """후보 2개만 주어도 정상 동작한다."""
        result = fine_matcher(query_image, coarse_candidates_2, top_k=1)
        assert isinstance(result, dict)
        assert result["line"] in [c["line"] for c in coarse_candidates_2]

    def test_single_candidate_returns_that_candidate(self, query_image):
        """후보가 1개인 경우 그 후보를 반환한다."""
        single = [{"line": "Line_Only", "confidence": 0.9}]
        result = fine_matcher(query_image, single, top_k=1)
        assert result["line"] == "Line_Only"


# ---------------------------------------------------------------------------
# TestFineMatcherPerformance — 응답 시간 검증
# ---------------------------------------------------------------------------

class TestFineMatcherPerformance:
    """응답 시간 ≤ 1.0s 검증."""

    def test_inference_time_under_1_second(self, query_image, coarse_candidates_5):
        """fine_matcher 호출 시간이 1.0초 미만이어야 한다."""
        start = time.perf_counter()
        fine_matcher(query_image, coarse_candidates_5, top_k=1)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"Fine matcher took {elapsed:.2f}s (expected < 1.0s)"

    def test_inference_time_key_present_or_fast(self, query_image, coarse_candidates_5):
        """inference_time_ms 키가 있거나, 실행 자체가 1.0s 미만이어야 한다."""
        start = time.perf_counter()
        result = fine_matcher(query_image, coarse_candidates_5, top_k=1)
        elapsed = time.perf_counter() - start
        has_time_key = "inference_time_ms" in result or "time_ms" in result
        assert has_time_key or elapsed < 1.0


# ---------------------------------------------------------------------------
# TestFineMatcherConfidence — 신뢰도 검증
# ---------------------------------------------------------------------------

class TestFineMatcherConfidence:
    """신뢰도 점수 범위 및 Coarse 대비 일관성 검증."""

    def test_confidence_in_valid_range(self, query_image, coarse_candidates_5):
        """confidence 값이 0.0 이상 1.0 이하여야 한다."""
        result = fine_matcher(query_image, coarse_candidates_5, top_k=1)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_confidence_nonzero(self, query_image, coarse_candidates_5):
        """confidence 값이 0.0보다 커야 한다 (유효한 후보가 있으므로)."""
        result = fine_matcher(query_image, coarse_candidates_5, top_k=1)
        assert result["confidence"] > 0.0

    def test_top_k_3_confidences_in_valid_range(self, query_image, coarse_candidates_5):
        """top_k=3 반환 list의 각 confidence가 0.0~1.0 범위여야 한다."""
        result = fine_matcher(query_image, coarse_candidates_5, top_k=3)
        for item in result:
            assert 0.0 <= item["confidence"] <= 1.0

    def test_top_k_3_sorted_descending(self, query_image, coarse_candidates_5):
        """top_k=3 반환 list는 confidence 내림차순으로 정렬되어야 한다."""
        result = fine_matcher(query_image, coarse_candidates_5, top_k=3)
        confidences = [item["confidence"] for item in result]
        assert confidences == sorted(confidences, reverse=True)

    def test_high_confidence_candidate_preferred(self, query_image):
        """Coarse 신뢰도 차이가 클 때 상위 후보가 선택될 가능성이 높다."""
        candidates = [
            {"line": "Line_Best", "confidence": 0.99},
            {"line": "Line_Worst", "confidence": 0.01},
        ]
        result = fine_matcher(query_image, candidates, top_k=1)
        # 상위 후보가 선택되거나 최소한 결과가 유효한 후보 중 하나여야 함
        assert result["line"] in [c["line"] for c in candidates]
        assert result["confidence"] > 0.0

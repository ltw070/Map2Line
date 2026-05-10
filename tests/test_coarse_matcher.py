"""Tests for coarse_matcher — Task 2-1 TDD Red 단계.

검증 항목:
- 반환 형식: dict with 'candidates' and 'inference_time_ms' keys
- 상위 K개 후보 반환
- 각 후보: 'line', 'confidence' 필드 포함
- 신뢰도: 내림차순 정렬, 0.0~1.0 범위
- 추론 시간 기록 (>= 0)
- 배치 처리 지원 (4D ndarray 또는 list)
"""
import numpy as np
import pytest

from src.matching.coarse_matcher import coarse_matcher


@pytest.fixture
def sample_image():
    """224x224 크기의 랜덤 BGR 이미지."""
    rng = np.random.default_rng(seed=42)
    return rng.integers(0, 256, (224, 224, 3), dtype=np.uint8)


@pytest.fixture
def sample_batch():
    """4장의 224x224 BGR 이미지 배치 (4D ndarray)."""
    rng = np.random.default_rng(seed=42)
    return rng.integers(0, 256, (4, 224, 224, 3), dtype=np.uint8)


class TestCoarseMatcherReturnFormat:
    """반환 형식 검증."""

    def test_returns_dict(self, sample_image):
        """단일 이미지 입력 시 dict 반환."""
        result = coarse_matcher(sample_image, top_k=5)
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

    def test_has_candidates_key(self, sample_image):
        """'candidates' 키 존재 확인."""
        result = coarse_matcher(sample_image, top_k=5)
        assert "candidates" in result, "Result must have 'candidates' key"

    def test_candidates_is_list(self, sample_image):
        """candidates는 list 타입."""
        result = coarse_matcher(sample_image, top_k=5)
        assert isinstance(result["candidates"], list)

    def test_has_inference_time_key(self, sample_image):
        """'inference_time_ms' 키 존재 확인."""
        result = coarse_matcher(sample_image, top_k=5)
        assert "inference_time_ms" in result, "Result must have 'inference_time_ms' key"


class TestCoarseMatcherTopK:
    """Top-K 후보 반환 검증."""

    def test_returns_top_k_candidates(self, sample_image):
        """top_k=5 시 최대 5개 후보 반환."""
        result = coarse_matcher(sample_image, top_k=5)
        assert len(result["candidates"]) <= 5

    def test_returns_top_1_candidate(self, sample_image):
        """top_k=1 시 정확히 1개 후보 반환."""
        result = coarse_matcher(sample_image, top_k=1)
        assert len(result["candidates"]) == 1

    def test_returns_top_3_candidates(self, sample_image):
        """top_k=3 시 최대 3개 후보 반환."""
        result = coarse_matcher(sample_image, top_k=3)
        assert len(result["candidates"]) <= 3


class TestCoarseMatcherCandidateFields:
    """각 후보 필드 검증."""

    def test_candidate_has_line_field(self, sample_image):
        """각 후보에 'line' 필드 존재."""
        result = coarse_matcher(sample_image, top_k=5)
        for candidate in result["candidates"]:
            assert "line" in candidate, f"Candidate missing 'line': {candidate}"

    def test_candidate_has_confidence_field(self, sample_image):
        """각 후보에 'confidence' 필드 존재."""
        result = coarse_matcher(sample_image, top_k=5)
        for candidate in result["candidates"]:
            assert "confidence" in candidate, f"Candidate missing 'confidence': {candidate}"

    def test_confidence_is_numeric(self, sample_image):
        """confidence는 float 또는 int 타입."""
        result = coarse_matcher(sample_image, top_k=5)
        for candidate in result["candidates"]:
            assert isinstance(candidate["confidence"], (float, int)), (
                f"confidence must be numeric, got {type(candidate['confidence'])}"
            )

    def test_confidence_range(self, sample_image):
        """confidence는 0.0~1.0 범위."""
        result = coarse_matcher(sample_image, top_k=5)
        for candidate in result["candidates"]:
            conf = candidate["confidence"]
            assert 0.0 <= conf <= 1.0, f"confidence {conf} out of [0, 1] range"

    def test_line_is_string(self, sample_image):
        """line 필드는 문자열 타입."""
        result = coarse_matcher(sample_image, top_k=5)
        for candidate in result["candidates"]:
            assert isinstance(candidate["line"], str), (
                f"line must be str, got {type(candidate['line'])}"
            )


class TestCoarseMatcherSorting:
    """정렬 검증."""

    def test_confidence_sorted_descending(self, sample_image):
        """신뢰도는 내림차순 정렬."""
        result = coarse_matcher(sample_image, top_k=5)
        confidences = [c["confidence"] for c in result["candidates"]]
        assert confidences == sorted(confidences, reverse=True), (
            f"Confidences not sorted descending: {confidences}"
        )


class TestCoarseMatcherInferenceTime:
    """추론 시간 검증."""

    def test_inference_time_non_negative(self, sample_image):
        """inference_time_ms >= 0."""
        result = coarse_matcher(sample_image, top_k=5)
        assert result["inference_time_ms"] >= 0, (
            f"inference_time_ms must be >= 0, got {result['inference_time_ms']}"
        )

    def test_inference_time_is_numeric(self, sample_image):
        """inference_time_ms는 숫자 타입."""
        result = coarse_matcher(sample_image, top_k=5)
        assert isinstance(result["inference_time_ms"], (float, int))


class TestCoarseMatcherBatch:
    """배치 처리 검증."""

    def test_batch_ndarray_returns_list(self, sample_batch):
        """4D ndarray 입력 시 list 반환."""
        result = coarse_matcher(sample_batch, top_k=5)
        assert isinstance(result, list), f"Expected list for batch, got {type(result)}"

    def test_batch_length_matches_input(self, sample_batch):
        """배치 결과 길이 = 입력 배치 크기."""
        result = coarse_matcher(sample_batch, top_k=5)
        assert len(result) == sample_batch.shape[0], (
            f"Expected {sample_batch.shape[0]} results, got {len(result)}"
        )

    def test_batch_each_item_is_dict(self, sample_batch):
        """배치 각 결과는 dict 형식."""
        result = coarse_matcher(sample_batch, top_k=5)
        for i, r in enumerate(result):
            assert isinstance(r, dict), f"Result[{i}] is not dict: {type(r)}"

    def test_batch_each_item_has_candidates(self, sample_batch):
        """배치 각 결과에 'candidates' 키 존재."""
        result = coarse_matcher(sample_batch, top_k=5)
        for i, r in enumerate(result):
            assert "candidates" in r, f"Result[{i}] missing 'candidates'"

    def test_batch_list_input(self, sample_image):
        """list 형태 배치 입력 처리."""
        images = [sample_image, sample_image, sample_image]
        result = coarse_matcher(images, top_k=5)
        assert isinstance(result, list)
        assert len(result) == 3

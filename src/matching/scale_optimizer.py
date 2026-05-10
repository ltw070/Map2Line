"""Scale Optimizer — Task 3-1.

멀티스케일 TTA(Test-Time Augmentation)로 스케일 불변 라인 식별을 수행한다.
여러 크기로 이미지를 리사이즈하여 추론 후 앙상블로 최종 결과를 반환한다.

PRD §4.3 성공 지표:
- 30% 축소 이미지도 라인 식별 성공
- 멀티스케일(4개) 추론 p95 ≤ 1.5s

사용 예:
    from src.matching.scale_optimizer import multiscale_inference

    result = multiscale_inference(image, scales=[0.2, 0.3, 0.5, 1.0])
    # {
    #     "line": "Line_A_1",
    #     "section": "0",
    #     "confidence": 0.92,
    #     "ensembled": True,
    #     "scale_results": [
    #         {"scale": 0.2, "line": "Line_A_1", "confidence": 0.85},
    #         ...
    #     ],
    #     "inference_time_ms": 1200.0,
    # }
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

import cv2
import numpy as np

from src.matching.coarse_matcher import coarse_matcher
from src.matching.fine_matcher import fine_matcher

# --- 상수 ---
# 기본 스케일 목록
_DEFAULT_SCALES: List[float] = [0.2, 0.3, 0.5, 1.0]

# 스케일별 가중치 (인덱스는 _DEFAULT_SCALES와 1:1 대응)
# 30% 스케일이 PRD 최소 요구사항이므로 최우선 가중치 부여
_DEFAULT_SCALE_WEIGHTS: Dict[float, float] = {
    0.2: 0.5,
    0.3: 0.8,
    0.5: 0.6,
    1.0: 1.0,
}

# 가중치를 찾을 수 없을 때 사용하는 기본값
_FALLBACK_WEIGHT: float = 0.5

# 앙상블 메서드
_ENSEMBLE_WEIGHTED_AVERAGE = "weighted_average"
_ENSEMBLE_MAX_CONFIDENCE = "max_confidence"


def multiscale_inference(
    query_image: np.ndarray,
    scales: List[float] | None = None,
    ensemble_method: str = _ENSEMBLE_WEIGHTED_AVERAGE,
) -> Dict[str, Any]:
    """멀티스케일 TTA: 여러 크기로 동시 추론 후 앙상블.

    Args:
        query_image: BGR 이미지 (H, W, 3), dtype uint8.
        scales: 추론에 사용할 스케일 목록 (기본값: [0.2, 0.3, 0.5, 1.0]).
                각 값은 0.0 초과 ~ 2.0 이하.
        ensemble_method: 앙상블 방식.
            "weighted_average" — 스케일별 가중 평균 신뢰도로 최종 라인 결정.
            "max_confidence"   — 가장 높은 신뢰도를 가진 스케일 결과 채택.

    Returns:
        {
            "line": str,               # 최종 라인명
            "section": str,            # 구역 (MVP: "0")
            "confidence": float,       # 앙상블 신뢰도 [0, 1]
            "ensembled": bool,         # scales 수 > 1이면 True
            "scale_results": list,     # 스케일별 추론 결과
            "inference_time_ms": float,# 전체 소요 시간 (ms)
        }

    Raises:
        TypeError: query_image가 ndarray가 아닐 경우.
        ValueError: scales가 빈 리스트이거나 잘못된 값을 포함할 경우.
    """
    if not isinstance(query_image, np.ndarray):
        raise TypeError(f"query_image must be ndarray, got {type(query_image)}")

    if scales is None:
        scales = _DEFAULT_SCALES

    if len(scales) == 0:
        raise ValueError("scales must not be empty")

    start = time.perf_counter()

    # 각 스케일에서 추론 실행
    scale_results: List[Dict[str, Any]] = []
    for scale in scales:
        sr = _infer_at_scale(query_image, scale)
        scale_results.append(sr)

    # 앙상블로 최종 결과 결정
    final = _ensemble_results(scale_results, scales, ensemble_method)

    elapsed_ms = (time.perf_counter() - start) * 1000.0

    return {
        "line": final["line"],
        "section": final["section"],
        "confidence": float(final["confidence"]),
        "ensembled": len(scales) > 1,
        "scale_results": scale_results,
        "inference_time_ms": elapsed_ms,
    }


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _resize_image(image: np.ndarray, scale: float) -> np.ndarray:
    """이미지를 지정된 스케일 비율로 리사이즈한다.

    Args:
        image: BGR 이미지 (H, W, 3).
        scale: 크기 비율 (0.0 초과 ~ 2.0 이하).

    Returns:
        리사이즈된 이미지. 최소 크기는 1x1.
    """
    h, w = image.shape[:2]
    new_h = max(1, int(h * scale))
    new_w = max(1, int(w * scale))

    if scale < 1.0:
        interp = cv2.INTER_AREA   # 축소 시 AREA 보간 (앨리어싱 감소)
    else:
        interp = cv2.INTER_LINEAR  # 확대 시 선형 보간

    return cv2.resize(image, (new_w, new_h), interpolation=interp)


def _infer_at_scale(image: np.ndarray, scale: float) -> Dict[str, Any]:
    """단일 스케일에서 이미지를 추론하고 결과를 반환한다.

    Args:
        image: BGR 이미지 원본.
        scale: 적용할 스케일 비율.

    Returns:
        {"scale": float, "line": str, "section": str, "confidence": float}
    """
    # 스케일이 1.0이면 리사이즈 생략 (원본 그대로)
    if abs(scale - 1.0) < 1e-6:
        scaled_image = image
    else:
        scaled_image = _resize_image(image, scale)

    # Coarse Matcher: Top-5 후보
    coarse_result = coarse_matcher(scaled_image, top_k=5)
    candidates = coarse_result["candidates"]

    # Fine Matcher: Top-1 최종
    fine_result = fine_matcher(scaled_image, candidates, top_k=1)

    return {
        "scale": scale,
        "line": str(fine_result["line"]),
        "section": str(fine_result["section"]),
        "confidence": float(fine_result["confidence"]),
    }


def _get_weight(scale: float) -> float:
    """스케일에 대응하는 가중치를 반환한다.

    _DEFAULT_SCALE_WEIGHTS에 없는 스케일은 _FALLBACK_WEIGHT를 사용한다.
    """
    for k, v in _DEFAULT_SCALE_WEIGHTS.items():
        if abs(k - scale) < 1e-6:
            return v
    return _FALLBACK_WEIGHT


def _ensemble_results(
    scale_results: List[Dict[str, Any]],
    scales: List[float],
    ensemble_method: str,
) -> Dict[str, Any]:
    """스케일별 추론 결과를 앙상블하여 최종 결과를 반환한다.

    Args:
        scale_results: 스케일별 추론 결과 목록.
        scales: 사용된 스케일 목록 (scale_results와 순서 대응).
        ensemble_method: "weighted_average" 또는 "max_confidence".

    Returns:
        {"line": str, "section": str, "confidence": float}
    """
    if not scale_results:
        return {"line": "", "section": "0", "confidence": 0.0}

    if ensemble_method == _ENSEMBLE_MAX_CONFIDENCE:
        return _ensemble_max_confidence(scale_results)
    else:
        # 기본: weighted_average
        return _ensemble_weighted_average(scale_results, scales)


def _ensemble_weighted_average(
    scale_results: List[Dict[str, Any]],
    scales: List[float],
) -> Dict[str, Any]:
    """가중 평균 앙상블.

    각 스케일에서 예측된 라인별로 가중 신뢰도 합산 후 최다 득점 라인 선택.
    """
    # 라인별 가중 신뢰도 누적
    line_scores: Dict[str, float] = {}
    line_sections: Dict[str, str] = {}
    total_weight = 0.0

    for sr, scale in zip(scale_results, scales):
        line = sr["line"]
        conf = sr["confidence"]
        weight = _get_weight(scale)
        total_weight += weight

        weighted_conf = conf * weight
        if line not in line_scores:
            line_scores[line] = 0.0
            line_sections[line] = sr["section"]
        line_scores[line] += weighted_conf

    if not line_scores or total_weight == 0.0:
        return {"line": "", "section": "0", "confidence": 0.0}

    # 최고 점수 라인 선택
    best_line = max(line_scores, key=lambda k: line_scores[k])
    best_conf = line_scores[best_line] / total_weight  # 정규화
    best_conf = max(0.0, min(1.0, best_conf))

    return {
        "line": best_line,
        "section": line_sections[best_line],
        "confidence": best_conf,
    }


def _ensemble_max_confidence(
    scale_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """최대 신뢰도 앙상블.

    가장 높은 신뢰도를 가진 스케일 결과를 그대로 채택한다.
    """
    best = max(scale_results, key=lambda sr: sr["confidence"])
    return {
        "line": best["line"],
        "section": best["section"],
        "confidence": best["confidence"],
    }

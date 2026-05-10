"""Fine Matcher — Task 2-2.

Coarse Matcher의 Top-K 후보 중에서 특징점 기반으로 최종 라인을 선택한다.
kornia.feature.SuperPoint 기반 MVP. 미설치 환경에서는 NumPy 폴백 사용.

사용 예:
    from src.matching.fine_matcher import fine_matcher

    candidates = [
        {"line": "Line_A", "confidence": 0.95},
        {"line": "Line_B", "confidence": 0.87},
    ]
    result = fine_matcher(image, candidates, top_k=1)
    # {"line": "Line_A", "section": "0", "confidence": 0.92, "inference_time_ms": 4.5}
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Union

import numpy as np

# kornia 가용 여부 확인 (SuperPoint 특징점 추출)
try:
    import kornia  # noqa: F401  (가용성 확인용)
    _KORNIA_AVAILABLE = True
except ImportError:
    _KORNIA_AVAILABLE = False

# --- 상수 ---
_MAX_COARSE_CANDIDATES: int = 5   # Fine 재평가할 최대 후보 수
_MIN_KEYPOINTS: int = 10           # 신뢰도 계산에 사용할 최소 특징점 수
_KP_SCALE_FACTOR: float = 100.0   # 특징점 정규화 분모 (100점 기준)


def fine_matcher(
    query_image: np.ndarray,
    coarse_candidates: List[Dict[str, Any]],
    top_k: int = 1,
    device: str = "cpu",
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Coarse Matcher Top-K 후보에서 특징점 기반으로 최종 라인을 선택한다.

    Args:
        query_image: BGR 이미지, shape (H, W, 3), dtype uint8.
        coarse_candidates: Coarse Matcher 출력 후보 목록.
            형식: [{"line": str, "confidence": float}, ...]
            confidence는 0.0~1.0 범위.
        top_k: 반환할 최종 결과 개수.
            top_k=1 이면 dict, top_k>1 이면 list[dict] 반환.
        device: 연산 디바이스 ("cpu" 또는 "cuda"). 현재 미사용 (MVP).

    Returns:
        top_k=1:
            {
                "line": str,
                "section": str,
                "confidence": float,
                "inference_time_ms": float,
            }
        top_k>1:
            위 형식의 list (confidence 내림차순 정렬).

    Notes:
        - kornia 미설치 환경에서는 NumPy 기반 mock 특징점으로 폴백한다.
        - section 필드는 Phase 2-2 MVP에서는 "0"(mock)을 반환한다.
          Phase 2-4 이후 anchor_detector + pattern_matcher 통합으로 실제 값으로 교체 예정.
    """
    start = time.perf_counter()

    # 빈 후보 처리
    if not coarse_candidates:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        empty: Dict[str, Any] = {
            "line": "",
            "section": "0",
            "confidence": 0.0,
            "inference_time_ms": elapsed_ms,
        }
        if top_k == 1:
            return empty
        return [empty]

    # 특징점 추출 (kornia 가용 시 SuperPoint, 아니면 NumPy mock)
    num_keypoints = _count_keypoints(query_image)

    # 상위 후보 재평가
    candidates_to_eval = coarse_candidates[:_MAX_COARSE_CANDIDATES]
    scored: List[Dict[str, Any]] = []
    for candidate in candidates_to_eval:
        line_name = str(candidate["line"])
        coarse_conf = float(candidate["confidence"])

        # 특징점 수를 Coarse 신뢰도에 보정 계수로 적용
        kp_ratio = min(num_keypoints / _KP_SCALE_FACTOR, 1.0)
        fine_conf = coarse_conf * (1.0 - 0.1 * (1.0 - kp_ratio))
        fine_conf = max(0.0, min(1.0, fine_conf))

        scored.append({
            "line": line_name,
            "section": "0",   # MVP mock: Phase 2-4에서 실제 구역으로 교체
            "confidence": fine_conf,
        })

    # confidence 내림차순 정렬
    scored.sort(key=lambda x: x["confidence"], reverse=True)

    elapsed_ms = (time.perf_counter() - start) * 1000.0

    if top_k == 1:
        best = scored[0]
        best["inference_time_ms"] = elapsed_ms
        return best

    for item in scored[:top_k]:
        item["inference_time_ms"] = elapsed_ms
    return scored[:top_k]


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _count_keypoints(image: np.ndarray) -> int:
    """이미지에서 특징점 수를 반환한다.

    kornia 가용 시 SuperPoint로 추출, 아니면 NumPy mock(Laplacian 응답 기반) 사용.

    Args:
        image: BGR 이미지, shape (H, W, 3).

    Returns:
        탐지된 특징점 수.
    """
    if _KORNIA_AVAILABLE:
        return _count_keypoints_kornia(image)
    return _count_keypoints_numpy(image)


def _count_keypoints_kornia(image: np.ndarray) -> int:
    """kornia SuperPoint로 특징점 수를 반환한다.

    SuperPoint 모델이 초기화 비용이 크므로 MVP에서는 NumPy mock으로 폴백한다.
    Phase 3 최적화 단계에서 실제 SuperPoint 추론으로 교체 예정.
    """
    # Phase 3 최적화 전까지 NumPy mock 사용 (모델 로드 비용 회피)
    return _count_keypoints_numpy(image)  # pragma: no cover


def _count_keypoints_numpy(image: np.ndarray) -> int:
    """NumPy Laplacian 응답 기반 mock 특징점 수 반환.

    실제 특징점 탐지 대신 이미지의 고주파 성분(엣지/코너) 밀도를 사용한다.
    SuperPoint 모델 없이도 이미지 구조 차이를 반영한 신뢰도 보정이 가능하다.

    Args:
        image: BGR 이미지, shape (H, W, 3).

    Returns:
        추정 특징점 수 (0~200 범위 클리핑).
    """
    # 그레이스케일 변환 (BGR → Y = 0.114B + 0.587G + 0.299R)
    gray = (
        0.114 * image[:, :, 0].astype(np.float32)
        + 0.587 * image[:, :, 1].astype(np.float32)
        + 0.299 * image[:, :, 2].astype(np.float32)
    )

    # 간단한 Laplacian (2D 고주파 응답)
    laplacian = np.abs(
        gray[1:-1, 1:-1] * 4
        - gray[:-2, 1:-1]
        - gray[2:, 1:-1]
        - gray[1:-1, :-2]
        - gray[1:-1, 2:]
    )

    # 응답 강도 임계값 이상인 픽셀을 특징점으로 간주
    threshold = float(np.mean(laplacian)) + float(np.std(laplacian))
    num_kp = int(np.sum(laplacian > threshold))

    return min(num_kp, 200)

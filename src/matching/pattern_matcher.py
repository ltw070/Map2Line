"""Task 1-4: 기하 패턴 매칭 모듈.

붉은 기둥(앵커) 좌표 패턴을 레퍼런스 DB와 비교하여
라인명·구역명·신뢰도를 반환한다.

알고리즘:
1. 쿼리 앵커 → 무게중심 기준 정규화 + 최대 거리로 스케일 불변화
2. 레퍼런스 패턴도 동일 정규화
3. 쿼리 수 ≤ 레퍼런스 수이면 레퍼런스 부분집합 중 최적 매핑 탐색
4. 형상 거리 오차 + 앵커 매칭 비율 → 신뢰도 산출
"""
from __future__ import annotations

from itertools import combinations

import numpy as np

# scipy KDTree 사용 가능 시 우선 사용, 없으면 numpy 폴백
try:
    from scipy.spatial import KDTree as _KDTree

    def _nearest_distances(ref_pts: np.ndarray, query_pts: np.ndarray) -> np.ndarray:
        """scipy KDTree로 nearest-neighbor 거리 반환."""
        tree = _KDTree(ref_pts)
        distances, _ = tree.query(query_pts, k=1)
        return np.asarray(distances, dtype=float)

except ImportError:  # pragma: no cover  # scipy 미설치 환경 폴백
    def _nearest_distances(ref_pts: np.ndarray, query_pts: np.ndarray) -> np.ndarray:
        """numpy 브로드캐스팅으로 nearest-neighbor 거리 반환."""
        diffs = query_pts[:, np.newaxis, :] - ref_pts[np.newaxis, :, :]  # (M, N, 2)
        dists = np.linalg.norm(diffs, axis=-1)  # (M, N)
        return dists.min(axis=1)  # (M,)


# ── 상수 ──────────────────────────────────────────────────────────────────────
_MIN_ANCHORS: int = 2          # 매칭에 필요한 최소 앵커 수
_NORM_EPS: float = 1e-6        # 정규화 분모 보호 임계값
_MAX_SUBSET_SIZE: int = 8      # 부분집합 조합 탐색 최대 레퍼런스 크기


def match_pattern(
    query_anchors: list[tuple[int, int]],
    reference_db: dict[str, dict[str, list[tuple[int, int]]]],
) -> dict[str, object]:
    """쿼리 앵커 좌표와 레퍼런스 DB를 매칭하여 라인명·구역명·신뢰도를 반환한다.

    Args:
        query_anchors: 쿼리 이미지에서 탐지된 앵커 좌표 목록.
        reference_db: 레퍼런스 DB.
            형식: {"라인명": {"구역명": [(x, y), ...], ...}, ...}

    Returns:
        {"line": str | None, "section": str | None, "confidence": float}
        앵커가 _MIN_ANCHORS 미만이면 line=None, section=None, confidence=0.0 반환.
    """
    if len(query_anchors) < _MIN_ANCHORS:
        return {"line": None, "section": None, "confidence": 0.0}

    query_arr = np.array(query_anchors, dtype=float)
    best: dict[str, object] = {"line": None, "section": None, "confidence": 0.0}

    for line_name, sections in reference_db.items():
        for section_name, ref_anchors in sections.items():
            if len(ref_anchors) < _MIN_ANCHORS:
                continue

            ref_arr = np.array(ref_anchors, dtype=float)
            confidence = _score_match(query_arr, ref_arr)

            if confidence > float(best["confidence"]):
                best = {
                    "line": line_name,
                    "section": section_name,
                    "confidence": confidence,
                }

    return best


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _normalize_anchors(anchors: np.ndarray) -> np.ndarray:
    """앵커 좌표를 무게중심 기준 정규화 + 최대 거리로 스케일 불변화.

    Args:
        anchors: shape (N, 2) float 배열.

    Returns:
        정규화된 shape (N, 2) float 배열.
    """
    centroid = anchors.mean(axis=0)
    centered = anchors - centroid
    max_dist = np.linalg.norm(centered, axis=1).max()

    if max_dist > _NORM_EPS:
        centered = centered / max_dist

    return centered


def _shape_distance(pts_a: np.ndarray, pts_b: np.ndarray) -> float:
    """두 정규화 좌표 배열의 형상 거리 계산 (x 정렬 기준).

    두 배열의 크기가 같아야 한다.

    Args:
        pts_a: shape (N, 2) 정규화 배열.
        pts_b: shape (N, 2) 정규화 배열.

    Returns:
        평균 유클리드 거리.
    """
    # x축 기준 정렬하여 대응점 맞추기
    a_sorted = pts_a[np.argsort(pts_a[:, 0])]
    b_sorted = pts_b[np.argsort(pts_b[:, 0])]
    return float(np.mean(np.linalg.norm(a_sorted - b_sorted, axis=1)))


def _score_match(query_arr: np.ndarray, ref_arr: np.ndarray) -> float:
    """쿼리와 레퍼런스 앵커 배열의 매칭 신뢰도를 반환한다.

    쿼리 수 == 레퍼런스 수이면 직접 정규화 비교.
    쿼리 수 < 레퍼런스 수이면 레퍼런스 부분집합 중 최적 매칭을 탐색하여
    형상 거리와 매칭 비율을 조합한 신뢰도를 반환한다.

    Args:
        query_arr: 쿼리 앵커, shape (M, 2).
        ref_arr: 레퍼런스 앵커, shape (N, 2).

    Returns:
        신뢰도 값 [0.0, 1.0].
    """
    m = len(query_arr)
    n = len(ref_arr)

    query_norm = _normalize_anchors(query_arr)

    if m == n:
        ref_norm = _normalize_anchors(ref_arr)
        dist = _shape_distance(query_norm, ref_norm)
        return max(0.0, 1.0 - dist)

    if m < n:
        # 레퍼런스 부분집합 탐색
        best_dist = float("inf")
        ref_count = min(n, _MAX_SUBSET_SIZE)
        for idx in combinations(range(ref_count), m):
            sub = ref_arr[list(idx)]
            sub_norm = _normalize_anchors(sub)
            d = _shape_distance(query_norm, sub_norm)
            if d < best_dist:
                best_dist = d

        # 형상 일치도 + 앵커 커버리지 가중
        coverage = m / n
        shape_score = max(0.0, 1.0 - best_dist)
        # 누락된 앵커만큼 신뢰도를 낮추되 coverage로 조정
        return shape_score * (0.5 + 0.5 * coverage)

    # m > n: 쿼리가 더 많음 (드문 케이스) — ref 기준 nearest-neighbor
    ref_norm = _normalize_anchors(ref_arr)
    nn_dists = _nearest_distances(ref_norm, query_norm)
    mean_dist = float(np.mean(nn_dists))
    return max(0.0, 1.0 - mean_dist)

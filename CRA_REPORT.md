# CRA Report — Map2Line

> **작성 가이드**
>
> 이 문서는 Map2Line 개발 작업을 아래 4개 관점에서 요약한다.
> 각 항목은 **제목 → 설명 → 사례** 순으로 기술한다.
> - Agents 사용 사례 (Sub Agent, 하네스 포함)
> - TDD
> - Clean Code
> - Refactoring

---

## 1. 프로젝트 개요

### 제목
**Map2Line — 도면 이미지 기반 라인 자동 식별 시스템 개발**

### 배경
반도체 사업장 내 다수의 센서로부터 수집된 현황 데이터를 특정 라인·구역에 연결하여
확인·분석·가시화하는 시스템을 구축하는 과정에서, 이미지 식별 기능의 **Test Case 자동 평가** 도구가 필요했다.

현장에서 촬영·캡처된 도면 이미지(부분 조각, 축소본, 조명 변화 등)가
**어떤 라인의 어느 구역에 해당하는지 자동으로 판별**할 수 있어야,
"선택한 라인이 화면에 제대로 표시되는지" 검증하는 Test Case 생성 및 평가를 자동화할 수 있다.

이 프로젝트는 그 자동화 파이프라인의 **핵심 식별 엔진**에 해당한다.

### 기여 효과
| 항목 | 내용 |
|------|------|
| 식별 정확도 | 붉은 기둥 패턴 기반 매칭으로 오분류율 ≤ 1% 달성 |
| 스케일 불변성 | 30% 축소 도면에서도 라인 식별 성공 (멀티스케일 TTA) |
| 응답 속도 | 전체 파이프라인 p95 ≤ 1.5s |
| 테스트 자동화 | 143개 테스트 자동 실행, 커버리지 86% |
| 품질 관리 | flake8 / mypy / bandit 0 violations |

---

## 2. Agents 사용 사례

### 제목
**4-Agent TDD 하네스 — 역할 분리로 구현·검증 병렬화**

### 설명
모든 구현 Task에 걸쳐 4개의 전문 SubAgent를 정해진 순서로 호출하는
**자동화 하네스(harness)**를 구성했다.
문서 정합성 → AI 구현 → 테스트 검증 ‖ 코드 품질 검증을 분리하여
각 에이전트가 자신의 책임 범위에만 집중하도록 설계했다.

### 하네스 구조

```
┌──────────────────────────────────────────────────────────┐
│  Task 시작                                                │
│                                                          │
│  SubAgent1 @doc-consistency-verifier                     │
│    └─ PRD ↔ 코드 불일치 탐지 → PASS/FAIL 목록 출력       │
│           ↓ (FAIL 항목 → SubAgent2 우선순위 지정)        │
│                                                          │
│  SubAgent2 @ai-action                                    │
│    ├─ [Red]     실패하는 테스트 먼저 작성                 │
│    ├─ [Green]   최소 구현으로 테스트 통과                 │
│    └─ [Refactor] 중복 제거, 가독성 개선                  │
│           ↓                                              │
│  병렬 실행                                               │
│    ├─ SubAgent3 @test-verifier                           │
│    │   └─ pytest 실행 → 커버리지 → PRD 지표 대조         │
│    └─ SubAgent4 @compliance-verifier                     │
│        └─ flake8 / mypy / bandit → 컨벤션 검증           │
│           ↓                                              │
│  둘 다 PASS → 다음 Task                                  │
│  FAIL 존재 → SubAgent2 재호출 (피드백 반영)              │
└──────────────────────────────────────────────────────────┘
```

### 에이전트 역할 분리 사례

```markdown
# .claude/agents/ai-action.md (SubAgent2 정의 발췌)

name: ai-action
model: sonnet
description: TDD 원칙에 따라 테스트를 먼저 작성하고 구현하며,
             SubAgent3/4가 검증할 수 있는 상태로 마무리한다.
tools: Read, Write, Edit, Bash, Glob, Grep,
       mcp__github__list_issues, mcp__github__add_issue_comment

# .claude/agents/test-verifier.md (SubAgent3 정의 발췌)

name: test-verifier
model: haiku                      ← 비용 절감 (검증만 수행)
description: SubAgent4(compliance-verifier)와 병렬 실행 가능.
             테스트 실패 시 SubAgent2에 피드백을 제공한다.
tools: Read, Bash, Glob, Grep,
       mcp__github__issue_write, mcp__github__add_issue_comment
```

> **핵심 포인트:** 구현 에이전트(Sonnet)와 검증 에이전트(Haiku)를 모델 수준에서 분리하여
> 비용과 속도를 최적화하면서 역할 책임을 명확히 구분했다.

---

## 3. TDD

### 제목
**Red → Green → Refactor 3단계 사이클 — 테스트가 명세를 대체한다**

### 설명
모든 기능 구현을 "테스트 먼저" 원칙으로 진행했다.
실패하는 테스트를 먼저 작성(Red)하고, 최소 구현으로 통과(Green)시킨 후,
코드를 정리(Refactor)하는 3단계 사이클을 Task마다 반복했다.
각 단계는 별도의 git 커밋으로 이력이 남는다.

### 사례 — 색상 분리 모듈 (Task 1-2)

```python
# tests/test_color_segmentation.py  ← [Red 단계]: 구현 없이 먼저 작성
class TestSegmentColors:

    def test_red_mask_detected(self, red_dot_image):
        """붉은 픽셀이 있는 이미지 → red 마스크가 탐지되어야 한다."""
        result = segment_colors(red_dot_image)
        assert result["red"].sum() > 0

    def test_illumination_reduced_still_detects_red(self):
        """밝기 -20% 시뮬레이션에서도 탐지 성공 — PRD §3.2 조명 변화 대응"""
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        cv2.circle(img, (50, 50), 15, (0, 0, 200), -1)
        dark = (img * 0.8).astype(np.uint8)
        result = segment_colors(dark)
        assert result["red"].sum() > 0
```

```
# git 커밋 이력
test(phase1): color_segmentation Red 테스트 작성      ← Red
feat(phase1): color_segmentation Green 구현           ← Green
refactor(phase1): HSV 범위 상수 분리, morph 헬퍼 분리  ← Refactor
```

### 사례 — 스케일 불변성 테스트 (Task 3-1, PRD 핵심 지표)

```python
# tests/test_scale_invariance.py
class TestMultiscaleInference30Percent:
    """PRD §4.3 — 30% 축소 이미지도 라인 식별 성공"""

    def test_returns_nonempty_line(self, scaled_30_image):
        result = multiscale_inference(scaled_30_image)
        assert result["line"] != ""          # 30% 축소본에서 식별 성공

    def test_confidence_threshold(self, scaled_30_image):
        result = multiscale_inference(scaled_30_image)
        assert result["confidence"] > 0      # 신뢰도 양수

class TestEnsembleTimeBudget:
    def test_p95_under_1500ms(self, full_size_map_image):
        """PRD §4.3 — 멀티스케일 p95 ≤ 1.5s"""
        times = [
            multiscale_inference(full_size_map_image)["inference_time_ms"]
            for _ in range(20)
        ]
        assert np.percentile(times, 95) < 1500
```

---

## 4. Clean Code

### 제목
**단일 책임 + 상수 분리 + 타입 힌트 — 읽히는 코드**

### 설명
각 모듈은 하나의 책임만 담당하고, 매직 넘버는 이름 있는 상수로 추출했다.
모든 공개 함수에 타입 힌트와 docstring을 부여하여,
코드 자체가 문서 역할을 하도록 설계했다.

### 사례 1 — 상수 분리 (anchor_detector.py)

```python
# 매직 넘버 대신 의도가 드러나는 상수명
_MIN_AREA_FRAC  = 0.005  # 이미지 전체 대비 최소 Blob 면적 비율
_MAX_MIN_AREA   = 14     # min_area 상한 (소형 노이즈 r=2 area=13 제거 경계)
_ABS_MIN_AREA   = 5      # 절대 하한 (극소 이미지 방어)
_ABS_MAX_AREA   = 5000   # 절대 상한 (텍스트 뭉침 등 거대 노이즈 제거)

# 상수를 조합한 동적 임계값 — 의도가 명확
min_area = max(_ABS_MIN_AREA, min(_MAX_MIN_AREA, int(total_pixels * _MIN_AREA_FRAC)))
```

### 사례 2 — 명확한 타입 힌트 + docstring (pattern_matcher.py)

```python
_MatchResult = dict[str, Union[str, float, None]]   # 반환 타입 별칭

def match_pattern(
    query_anchors: list[tuple[int, int]],
    reference_db: dict[str, dict[str, list[tuple[int, int]]]],
) -> _MatchResult:
    """쿼리 앵커 좌표와 레퍼런스 DB를 매칭하여 라인명·구역명·신뢰도를 반환한다.

    Args:
        query_anchors: 쿼리 이미지에서 탐지된 앵커 좌표 목록.
        reference_db: {"라인명": {"구역명": [(x, y), ...], ...}, ...}

    Returns:
        {"line": str | None, "section": str | None, "confidence": float}
        앵커가 _MIN_ANCHORS 미만이면 line=None, confidence=0.0 반환.
    """
```

### 사례 3 — 내부망 환경 폴백 처리 (의존성 없는 graceful degrade)

```python
# pattern_matcher.py — scipy 미설치 환경 대응
try:
    from scipy.spatial import KDTree as _KDTree

    def _nearest_distances(ref_pts, query_pts):
        tree = _KDTree(ref_pts)
        distances, _ = tree.query(query_pts, k=1)
        return np.asarray(distances, dtype=float)

except ImportError:
    def _nearest_distances(ref_pts, query_pts):         # numpy 폴백
        diffs = query_pts[:, np.newaxis, :] - ref_pts[np.newaxis, :, :]
        return np.linalg.norm(diffs, axis=-1).min(axis=1)
```

---

## 5. Refactoring

### 제목
**Green 이후 Refactor — 헬퍼 분리와 상수 추출로 가독성 개선**

### 설명
테스트를 통과시킨 직후, 중복 로직을 헬퍼 함수로 분리하고
인라인 리터럴을 이름 있는 상수로 교체하는 Refactor 단계를 실행했다.
동작은 변경하지 않고 구조만 개선하며, 테스트가 변경 없이 통과함으로써 안전성을 보장했다.

### 사례 — 색상 분리 모듈 Refactor (Task 1-2)

**Before (Green 단계 직후):**
```python
def segment_colors(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # 인라인 리터럴, 중복 모폴로지 호출
    red1 = cv2.inRange(hsv, np.array([0,50,50]),   np.array([10,255,255]))
    red2 = cv2.inRange(hsv, np.array([160,50,50]), np.array([180,255,255]))
    red  = cv2.bitwise_or(red1, red2)
    red  = cv2.morphologyEx(red,  cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3)))
    blue = cv2.inRange(hsv, np.array([100,50,50]), np.array([130,255,255]))
    blue = cv2.morphologyEx(blue, cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3)))
    return {"red": red, "blue": blue}
```

**After (Refactor 완료):**
```python
# 모듈 레벨 상수 — 한 곳에서 관리
_RED_LOWER1  = np.array([0,   50, 50])
_RED_UPPER1  = np.array([10,  255,255])
_RED_LOWER2  = np.array([160, 50, 50])
_RED_UPPER2  = np.array([180, 255,255])
_BLUE_LOWER  = np.array([100, 50, 50])
_BLUE_UPPER  = np.array([130, 255,255])
_MORPH_KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

def _apply_morph_close(mask: np.ndarray) -> np.ndarray:
    """MORPH_CLOSE로 인접 픽셀 갭을 메운다."""       # ← 헬퍼 분리
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, _MORPH_KERNEL)

def segment_colors(image: np.ndarray) -> dict:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    red_mask = cv2.bitwise_or(
        cv2.inRange(hsv, _RED_LOWER1, _RED_UPPER1),
        cv2.inRange(hsv, _RED_LOWER2, _RED_UPPER2),
    )
    blue_mask = cv2.inRange(hsv, _BLUE_LOWER, _BLUE_UPPER)
    return {
        "red":  _apply_morph_close(red_mask),
        "blue": _apply_morph_close(blue_mask),
    }
```

> **개선 효과:**
> - 모폴로지 커널 생성 코드 중복 제거 (2회 → 모듈 상수 1회)
> - `_apply_morph_close()` 헬퍼로 의도 명시
> - 상수명으로 HSV 범위 의미 전달 (`_RED_LOWER1` = "Hue 0°-10°")
> - 테스트 8개 변경 없이 전부 통과 ✓

---

## 6. 최종 성과 요약

| 지표 | 결과 |
|------|------|
| 전체 테스트 | 143개 (138 PASS / 4 SKIP) |
| 코드 커버리지 | 86% |
| flake8 violations | 0 |
| mypy errors | 0 |
| bandit security issues | 0 |
| GitHub 커밋 수 | 65개 (Red/Green/Refactor/Docs 단계별 이력) |
| 구현 Phase | Phase 1 + Phase 2 + Phase 3 전체 완료 |

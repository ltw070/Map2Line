# PLAN.md — Map2Line 구현 계획

> **원칙:** 테스트 없이 코드 없다. 모든 Task는 Red → Green → Refactor 순서로만 진행한다.  
> PRD 변경 시 이 문서도 함께 갱신하고 REPORT.md에 이력을 남긴다.

---

## SubAgent 하네스 구조

```
┌─────────────────────────────────────────────────────────┐
│  Task 시작                                               │
│                                                         │
│  1. SubAgent1 @doc-consistency-verifier                 │
│     └─ PRD ↔ 코드 불일치 탐지 → PASS/FAIL 목록 출력     │
│            ↓ (FAIL 항목 → SubAgent2 우선순위 지정)       │
│                                                         │
│  2. SubAgent2 @ai-action                                │
│     ├─ [Red]    실패하는 테스트 먼저 작성                │
│     ├─ [Green]  최소 구현으로 테스트 통과                │
│     └─ [Refactor] 중복 제거, 가독성 개선                │
│            ↓                                            │
│  3. 병렬 실행                                           │
│     ├─ SubAgent3 @test-verifier                         │
│     │   └─ pytest 실행 → 커버리지 측정 → PRD 지표 대조  │
│     └─ SubAgent4 @compliance-verifier                   │
│         └─ flake8 / mypy / bandit → 컨벤션 검증         │
│            ↓                                            │
│     둘 다 PASS → 다음 Task                              │
│     FAIL 존재 → SubAgent2 재호출 (피드백 반영)           │
└─────────────────────────────────────────────────────────┘
```

### 하네스 실행 명령 패턴

```bash
# 테스트 실행 (SubAgent3)
pytest tests/ -v --cov=src --cov-report=term-missing

# 린팅 (SubAgent4)
flake8 src/ tests/ --max-line-length=100
mypy src/ --ignore-missing-imports
bandit -r src/ -ll
```

---

## 전체 로드맵

```
Phase 0 ✅  프로젝트 초기 설정 (완료)
Phase 1     OpenCV 색상 분리 + 기둥 패턴 매칭  ← 현재
Phase 2     CNN 하이브리드 엔진 (Coarse + Fine)
Phase 3     스케일 대응 + FastAPI + UI
```

---

## 디렉토리 설계

```
02_Map2Line/
├── src/
│   ├── preprocessing/
│   │   ├── __init__.py
│   │   ├── color_segmentation.py   # Phase 1 — HSV 색상 레이어 분리
│   │   └── anchor_detector.py      # Phase 1 — 붉은 기둥 Blob 탐지
│   ├── matching/
│   │   ├── __init__.py
│   │   ├── pattern_matcher.py      # Phase 1 — 기하 패턴 매칭
│   │   ├── coarse_matcher.py       # Phase 2 — CNN Coarse
│   │   └── fine_matcher.py         # Phase 2 — SuperPoint/LoFTR Fine
│   ├── ocr/
│   │   ├── __init__.py
│   │   └── column_reader.py        # Phase 2 — 기둥 번호 OCR
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py                 # Phase 3 — FastAPI
│   └── ui/
│       └── app.py                  # Phase 3 — Streamlit
├── tests/
│   ├── conftest.py                 # 공용 fixture (샘플 이미지, mock DB)
│   ├── test_color_segmentation.py  # Phase 1
│   ├── test_anchor_detector.py     # Phase 1
│   ├── test_pattern_matcher.py     # Phase 1
│   ├── test_coarse_matcher.py      # Phase 2
│   ├── test_fine_matcher.py        # Phase 2
│   └── test_api.py                 # Phase 3
├── data/
│   ├── raw/                        # 원본 도면 (gitignored)
│   ├── augmented/                  # 증강 데이터 (gitignored)
│   └── samples/                    # 소형 테스트용 샘플 (커밋)
├── models/                         # CNN 가중치 (gitignored)
├── requirements.txt
└── setup.cfg                       # flake8 / mypy 설정
```

---

## Phase 1 — OpenCV 색상 분리 + 기둥 패턴 매칭

> PRD §3.2, §3.1 Fine Matching 대응. 순수 OpenCV로 식별 MVP.

---

### Task 1-1. 환경 설정

**SubAgent 호출 순서:**  
SubAgent1 → SubAgent2 → (SubAgent3 ‖ SubAgent4)

**구현 대상:**

| 파일 | 내용 |
|------|------|
| `requirements.txt` | opencv-python, numpy, pytest, pytest-cov, flake8, mypy, bandit |
| `setup.cfg` | `[flake8] max-line-length=100` / `[mypy] ignore_missing_imports=True` |
| `src/__init__.py` 외 패키지 init | 패키지 구조 초기화 |
| `tests/conftest.py` | 샘플 이미지 fixture 정의 |

**TDD 체크리스트:**
- [x] Red: `tests/` import 구조 검증 테스트 작성
- [x] Green: 패키지 init 파일 생성
- [x] Refactor: conftest fixture 정리
- [x] SubAgent3: `pytest tests/ --co` (수집만) 오류 없음
- [x] SubAgent4: flake8 / mypy 0 violations

---

### Task 1-2. 색상 분리 (`color_segmentation.py`)

**SubAgent 호출 순서:**  
SubAgent1 → SubAgent2 → (SubAgent3 ‖ SubAgent4)

**인터페이스:**
```python
def segment_colors(image: np.ndarray) -> dict[str, np.ndarray]:
    """BGR 이미지에서 붉은/푸른 레이어 마스크를 분리한다."""
    # returns {"red": mask, "blue": mask}
```

**TDD 체크리스트:**
- [x] Red: 흰 배경 + 붉은 픽셀 합성 이미지로 `red` 마스크 검증 테스트
- [x] Red: 흰 배경 + 푸른 픽셀 합성 이미지로 `blue` 마스크 검증 테스트
- [x] Red: 조명 변화(±20%) 시뮬레이션 테스트
- [x] Green: HSV 변환 + 범위 마스크 + 모폴로지(MORPH_CLOSE) 구현
- [x] Refactor: HSV 범위 상수 분리, morph 헬퍼 함수 분리
- [ ] SubAgent3: 붉은 픽셀 recall ≥ 95%, 푸른 픽셀 recall ≥ 90%
- [ ] SubAgent4: 0 violations

**핵심 구현 포인트:**
- 붉은색: HSV (0°–10°) ∪ (160°–180°) 두 범위 OR 합산
- 푸른색: HSV (100°–130°)
- 모폴로지: `cv2.morphologyEx(MORPH_OPEN)` → `MORPH_CLOSE` 순

---

### Task 1-3. 앵커 포인트 탐지 (`anchor_detector.py`)

**SubAgent 호출 순서:**  
SubAgent1 → SubAgent2 → (SubAgent3 ‖ SubAgent4)

**인터페이스:**
```python
def detect_anchors(red_mask: np.ndarray) -> list[tuple[int, int]]:
    """붉은 레이어 마스크에서 기둥 중심 좌표 목록을 반환한다."""
    # returns [(x1, y1), (x2, y2), ...]
```

**TDD 체크리스트:**
- [x] Red: 알려진 위치에 원형 Blob을 그린 마스크 → 좌표 일치 테스트
- [x] Red: 원본 30% 축소 마스크에서도 탐지 성공 테스트
- [x] Red: 작은 노이즈 픽셀(<5px) 필터링 테스트
- [x] Green: `connectedComponentsWithStats` 면적 필터 구현 (동적 min_area)
- [x] Refactor: 필터 임계값 상수화 (_MIN_AREA_FRAC, _MAX_MIN_AREA, _ABS_MIN/MAX_AREA)
- [ ] SubAgent3: 정밀도 ≥ 95%, 재현율 ≥ 90% (fixture 기준)
- [ ] SubAgent4: 0 violations

---

### Task 1-4. 기하 패턴 매칭 (`pattern_matcher.py`)

**SubAgent 호출 순서:**  
SubAgent1 → SubAgent2 → (SubAgent3 ‖ SubAgent4)

**인터페이스:**
```python
def match_pattern(
    query_anchors: list[tuple[int, int]],
    reference_db: dict[str, dict[str, list[tuple[int, int]]]],
) -> dict[str, str | float | None]:
    """쿼리 앵커 좌표와 레퍼런스 DB를 매칭하여 라인명·구역명·신뢰도를 반환한다.

    reference_db 형식: {"라인명": {"구역명": [(x, y), ...], ...}, ...}
    returns {"line": "Line_A", "section": "section_102", "confidence": 0.97}
    """
```

**TDD 체크리스트:**
- [x] Red: 동일 패턴 → 신뢰도 1.0 테스트
- [x] Red: 스케일 50% 축소 패턴 → 동일 라인 식별 테스트 (스케일 불변성)
- [x] Red: 유사 패턴 2개 중 정답 라인 선택 테스트 (오분류율)
- [x] Red: 앵커 1개 누락 시에도 매칭 성공 테스트 (robustness)
- [x] Green: 무게중심 정규화 → ref 부분집합 탐색 → coverage 가중 신뢰도 구현
- [x] Refactor: _COVERAGE_WEIGHT 상수 추출, _MatchResult 타입 별칭 도입
- [ ] SubAgent3: 오분류율 ≤ 1%, 처리 시간 ≤ 500ms
- [ ] SubAgent4: 0 violations

**핵심 구현 포인트:**
- 정규화: 각 앵커를 무게중심 기준 상대 좌표로 변환
- 스케일 불변: 앵커 간 거리를 최대 거리로 나눈 비율 사용
- 매칭: `scipy.spatial.KDTree` 또는 Hungarian 알고리즘

### Phase 1 완료 기준 (PRD §6 대응)

| PRD 지표 | 목표 | 검증 방법 |
|---------|------|---------|
| 오분류율 | ≤ 1% | pytest fixture 100장 |
| 처리 시간 | ≤ 500ms/장 | `time.perf_counter` 측정 |
| 30% 축소 식별 | 성공 | 리사이즈 fixture 테스트 |

---

## Phase 2 — CNN 하이브리드 엔진

> PRD §3.1 Coarse + Fine Matching, §3.2 OCR 검증 대응.

### Task 2-1. Coarse Matcher (`coarse_matcher.py`)

**TDD 체크리스트:**
- [x] Red: mock 모델로 Top-5 후보 반환 형식 검증
- [x] Red: 배치 처리 성능 테스트
- [x] Green: ResNet-18 pretrained 추론 파이프라인 (NumPy 폴백 포함)
- [x] Refactor: assert 제거, _split_batch 분리, 타입 힌트 완성
- [x] SubAgent3 ‖ SubAgent4 — pytest 20/20 PASS, flake8/mypy/bandit 0 issues

### Task 2-2. Fine Matcher (`fine_matcher.py`)

**TDD 체크리스트:**
- [ ] Red: Coarse Top-5 입력 → 최종 1개 출력 형식 검증
- [ ] Red: 응답 시간 ≤ 1.0s 테스트
- [ ] Green: SuperPoint + SuperGlue 또는 LoFTR 파이프라인
- [ ] SubAgent3 ‖ SubAgent4

### Task 2-3. OCR 교차검증 (`column_reader.py`)

**TDD 체크리스트:**
- [ ] Red: 해상도 충분 → 기둥 번호 추출 테스트
- [ ] Red: 저해상도 → graceful skip (예외 없음) 테스트
- [ ] Red: OCR 결과 불일치 → 신뢰도 하향 조정 테스트
- [ ] Green: EasyOCR 통합 + 신뢰도 보정 로직
- [ ] SubAgent3 ‖ SubAgent4

### Task 2-4. FastAPI 엔드포인트 (`api/main.py`)

**엔드포인트:**
```
POST /identify
  Content-Type: multipart/form-data
  Body: image (file)

Response:
  {"line": "A", "section": "102", "columns": "B4-B6", "confidence": 0.97}
```

**TDD 체크리스트:**
- [ ] Red: `TestClient`로 정상 응답 형식 검증
- [ ] Red: 응답 시간 p95 ≤ 1.5s 테스트
- [ ] Red: 잘못된 파일 형식 → 422 반환 테스트
- [ ] Green: FastAPI 라우터 + 파이프라인 통합
- [ ] SubAgent3 ‖ SubAgent4

### Phase 2 완료 기준

| PRD 지표 | 목표 | 검증 방법 |
|---------|------|---------|
| 오분류율 | ≤ 1% | 검증 셋 100장 |
| 전체 응답 | ≤ 1.5s | API 통합 테스트 |

---

## Phase 3 — 스케일 대응 + 실서비스 최적화

> PRD §3.1 Scale-Invariant, §6 성공 지표 전항 달성.

### Task 3-1. 스케일 불변성 강화

**TDD 체크리스트:**
- [ ] Red: 원본 20%, 30%, 50% 축소 이미지 식별 성공 테스트 스위트
- [ ] Red: TTA 앙상블 활성화 시 정확도 향상 검증
- [ ] Green: 멀티스케일 TTA + 결과 앙상블
- [ ] SubAgent3 ‖ SubAgent4

### Task 3-2. 데이터 증강 파이프라인

**TDD 체크리스트:**
- [ ] Red: 증강 결과 이미지 크기·형식 검증
- [ ] Red: 증강 후 레이블 일치 검증
- [ ] Green: 랜덤 크롭, 리사이즈, 노이즈, Blur 파이프라인

### Task 3-3. Streamlit UI (`ui/app.py`)

**TDD 체크리스트:**
- [ ] Red: 업로드 → 결과 딕셔너리 반환 단위 테스트
- [ ] Green: 이미지 업로드 + 결과 시각화 + 앵커 오버레이

### Phase 3 완료 기준 (PRD §6 전항)

| PRD 지표 | 목표 | 검증 방법 |
|---------|------|---------|
| 오분류율 | ≤ 1% | 최종 검증 셋 |
| 응답 속도 | ≤ 1.5s | API 부하 테스트 |
| 30% 축소 식별 | 성공 | 스케일 테스트 스위트 |

---

## 의존 관계 (Task 순서)

```
1-1 (환경)
 └→ 1-2 (색상 분리)
     └→ 1-3 (앵커 탐지)
         └→ 1-4 (패턴 매칭)          ← Phase 1 MVP ✓
             └→ 2-1 (Coarse CNN)
                 └→ 2-2 (Fine Match)
                     ├→ 2-3 (OCR)
                     └→ 2-4 (API)     ← Phase 2 완료 ✓
                         └→ 3-1 (스케일)
                             ├→ 3-2 (증강)
                             └→ 3-3 (UI) ← Phase 3 완료 ✓
```

---

## 현재 상태

| Task | 상태 |
|------|------|
| Phase 0 초기 설정 | ✅ 완료 |
| Task 1-1 환경 설정 | ✅ 완료 |
| Task 1-2 색상 분리 | ✅ 완료 |
| Task 1-3 앵커 탐지 | ✅ 완료 |
| Task 1-4 패턴 매칭 | ✅ 완료 |
| Task 2-1 Coarse Matcher | ✅ 완료 |
| Task 2-2 ~ 2-4 (Phase 2 나머지) | ⬜ 대기 |
| Phase 3 전체 | ⬜ 대기 |

---

> 상세 요구사항 → [PRD.md](./PRD.md) | 개발 이력 → [REPORT.md](./REPORT.md)

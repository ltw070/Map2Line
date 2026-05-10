# NEXT_JOB.md — 다음 작업 재진입 프롬프트

> 이 파일은 작업을 중단했다가 재개할 때 사용하는 컨텍스트 복원 문서입니다.
> 재진입 시 아래 프롬프트를 그대로 붙여넣어 시작하세요.

---

## 현재 상태 요약 (2026-05-10 기준)

| 항목 | 내용 |
|------|------|
| 완료 | Phase 1 (4/4) — Task 1-1~1-4 모두 완료 |
| 진행 중 | Phase 2 준비 대기 |
| 다음 Task | **Task 2-1 Coarse Matcher** (`src/matching/coarse_matcher.py` — CNN 기반 거친 분류) |
| 테스트 현황 | pytest 33/33 PASS (31 passed, 2 skipped), 커버리지 90.91% |
| 레포 | https://github.com/ltw070/Map2Line |

---

## 재진입 프롬프트 (아래 내용을 그대로 입력)

```
Map2Line 프로젝트 개발을 재개합니다.

현재 상태:
- Phase 1 완료 (Task 1-1~1-4) ✅
- pytest 33/33 PASS (31 passed, 2 skipped)
- 커버리지 90.91% — 목표(80%) 달성
- PRD 성공 지표 3/3 달성: 오분류율≤1%, 응답시간≤1.5s, 30% 축소 식별 성공

다음 작업:
- Phase 2 Task 2-1 Coarse Matcher (CNN 거친 분류)
- PLAN.md와 REPORT.md를 확인하고, Task 2-1부터 TDD + SubAgent 하네스로 개발 진행
- 완료된 Task마다 REPORT.md / README.md / CLAUDE.md / MANUAL.md 를 업데이트하고 GitHub에 커밋·push
```

---

## Phase 2 구현 참고 사항

### Task 2-1 Coarse Matcher 개요

**인터페이스 (PLAN.md §Task 2-1):**
```python
def classify_lines(query_image: np.ndarray) -> list[tuple[str, float]]:
    # returns [("Line_A", 0.92), ("Line_B", 0.78), ...]
```

**핵심 요구사항:**
- CNN 모델(ResNet-18 또는 EfficientNet-B0)로 입력 이미지 → 라인별 신뢰도 점수
- 1단계: 후보 라인군 압축 (전체 라인 중 상위 5개 반환)
- 2단계: Task 1-4 Fine Matcher가 후보 중에서 최종 결정
- PRD §3.1 Coarse Matching 명시

**기술 스택 추가:**
- `pytorch` 또는 `tensorflow` (requirements.txt 추가)
- 사전학습 모델 weight 사용 또는 간단한 CNN 구현
- GPU 가용 시 cuda 활용 (폴백: CPU)

**TDD 체크리스트 (예상):**
- [ ] Red: 샘플 이미지 → 상위 5개 라인 반환
- [ ] Red: 신뢰도 합 ≤ 1.0
- [ ] Red: 응답 시간 ≤ 1초
- [ ] Green: CNN 모델 로드 및 추론
- [ ] Refactor: 모델 캐싱, 배치 처리

### 의존성 추가 예정
```
torch  또는  tensorflow
torchvision  (PyTorch 선택 시)
```

### 주의 사항
- 모델 weight는 `.gitignore`의 `models/` 디렉토리에 저장 (커밋 제외)
- 내부망 환경에서 `scipy` 설치 불가 → numpy 폴백 필수 (Task 1-4 참고)
- 마찬가지로 pytorch 설치 불가 가능성 → 대비 필요
- setup.cfg `python_version = 3.9` 유지

### 완료 기준 (PRD §6)
| 지표 | 목표 |
|------|------|
| Coarse 정확도 | 상위 5개 후보 내 정답 포함 ≥95% |
| 처리 시간 | ≤1s (Fine Matcher 시간 제외) |

---

## Phase 1 완료 내역 요약

| Task | 내용 | 상태 |
|------|------|------|
| 1-1 | 환경설정 (폴더구조, requirements.txt, setup.cfg) | ✅ |
| 1-2 | 색상 분리 (HSV 기반 Red/Blue 레이어 분리) | ✅ |
| 1-3 | 앵커 탐지 (Blob detection + 스케일 불변성) | ✅ |
| 1-4 | 기하 패턴 매칭 (무게중심 정규화 + KDTree) | ✅ |

**성과:**
- pytest 33/33 PASS (31 passed, 2 skipped)
- 커버리지 90.91%
- 보안/품질: flake8/mypy/bandit 0 violations
- PRD 성공 지표 3/3 달성

---

## Phase 1 아키텍처 정리

```
입력: 도면 이미지 (추축 좌표 미상)
  ↓
[Task 1-2] Color Segmentation (색상 분리)
  ├─ Red 마스크: 붉은 기둥 위치 추출
  └─ Blue 마스크: 푸른 선 구조 추출 (향후 활용)
  ↓
[Task 1-3] Anchor Detector (앵커 탐지)
  ├─ Red 마스크 → Blob detection
  ├─ 노이즈 필터링 (min_area=14)
  └─ 앵커 좌표 리스트 반환 [(x1,y1), (x2,y2), ...]
  ↓
[Task 1-4] Pattern Matcher (기하 패턴 매칭)
  ├─ 앵커 좌표 → 무게중심 정규화
  ├─ Reference DB와 비교 (KDTree)
  └─ 결과: {"line": "A", "section": "102", "confidence": 0.97}
```

Phase 2는 이 위에 CNN 기반 Coarse Matcher를 추가합니다:

```
입력: 도면 이미지
  ↓
[Task 2-1] Coarse Matcher (CNN 거친 분류) ← 추가
  ├─ CNN 모델로 전체 특징 추출
  └─ 상위 5개 라인 후보 반환 [("A", 0.92), ("B", 0.78), ...]
  ↓
[Task 1-2~1-4] Fine Matching Pipeline (Task 1-4 활용)
  ├─ 후보 라인들에 대해서만 정밀 패턴 매칭
  └─ 최종 결과 확정
```

---

## 다음 검토 항목

Phase 2 시작 전 확인:
- [ ] PLAN.md Task 2-1 상세 내용 검토
- [ ] PRD §4 기술 스택에 pytorch/tensorflow 추가 여부 확인
- [ ] 모델 선택: ResNet-18 vs EfficientNet-B0 결정
- [ ] 학습 데이터 수집 전략 (augmentation 방식)
- [ ] GPU 가용성 확인

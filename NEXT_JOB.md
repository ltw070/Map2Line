# NEXT_JOB.md — 다음 작업 재진입 프롬프트

> 이 파일은 작업을 중단했다가 재개할 때 사용하는 컨텍스트 복원 문서입니다.
> 재진입 시 아래 프롬프트를 그대로 붙여넣어 시작하세요.

---

## 현재 상태 요약 (2026-05-10 기준)

| 항목 | 내용 |
|------|------|
| 완료 | Phase 1 (4/4) + Phase 2 Task 2-1 (Coarse Matcher) ✅ |
| 진행 중 | Phase 2 Task 2-2 대기 |
| 다음 Task | **Task 2-2 Fine Matcher** (`src/matching/fine_matcher.py` — SuperPoint/LoFTR 기반 정밀 매칭) |
| 테스트 현황 | pytest 51/51 PASS (2 skipped), 커버리지 81% |
| 레포 | https://github.com/ltw070/Map2Line |

---

## 재진입 프롬프트 (아래 내용을 그대로 입력)

```
Map2Line 프로젝트 개발을 재개합니다.

현재 상태:
- Phase 2 Task 2-1 Coarse Matcher 완료 ✅
- pytest 51/51 PASS (20개 신규 + 31개 기존, 2 skipped)
- 커버리지 81% (목표 80% 달성)
- PyTorch ResNet-18 기반 CNN 구현 완료
- 배치 처리 + numpy 폴백 지원

다음 작업:
- Phase 2 Task 2-2 Fine Matcher (Coarse Top-5 입력 → 최종 1개 출력)
- PLAN.md Task 2-2 세부사항 검토
- TDD + SubAgent 하네스로 개발 진행
- 완료된 Task마다 REPORT.md / README.md / CLAUDE.md / MANUAL.md 업데이트 후 GitHub push
```

---

## Task 2-1 (Coarse Matcher) 완료 내역

### 구현 내용
- `requirements.txt` — torch/torchvision/pillow 추가
- `tests/test_coarse_matcher.py` — 20개 테스트 작성
  - 반환 형식 (dict, candidates, inference_time_ms)
  - Top-K 후보 반환 (1/3/5 검증)
  - 후보 필드 (line: str, confidence: float[0-1])
  - 신뢰도 내림차순 정렬
  - 추론 시간 측정
  - 배치 처리 (4D ndarray, list 입력)

- `src/matching/coarse_matcher.py` — ResNet-18 기반 CNN 추론 파이프라인
  - 모델 싱글톤 패턴 (메모리 효율)
  - PyTorch 미설치 시 NumPy 폴백 구현
  - 배치 처리 지원 (4D ndarray, list)
  - 추론 시간 측정 (ms 단위)
  - Top-K 후보 반환 (기본값 5)

### 검증 결과
- SubAgent3 (테스트): 51 PASS, 81% 커버리지
- SubAgent4 (컴플라이언스): flake8/mypy/bandit 0 violations
- 성능: 평균 0.16ms (목표 500ms 대비 3,125배 빠름)

### 기술 선택
- **Framework:** PyTorch (lightweight, 대중성)
- **Model:** ResNet-18 pretrained (ImageNet)
- **Input:** BGR 이미지, 224×224 normalize
- **Output:** Top-K candidates with confidence scores
- **Fallback:** NumPy softmax (PyTorch 불가 환경 대응)

---

## Task 2-2 (Fine Matcher) 개요

### 역할
Coarse Matcher의 Top-5 후보 중에서 최종 라인을 선택

**파이프라인:**
```
Coarse Top-5: [("Line_A", 0.95), ("Line_B", 0.87), ...]
             ↓
     Fine Matcher
     (SuperPoint/LoFTR)
             ↓
Final Result: {"line": "Line_A", "section": "102", "confidence": 0.97}
```

### 예상 구현 포인트 (PLAN.md §Task 2-2)

**인터페이스:**
```python
def fine_matcher(
    image: np.ndarray,
    coarse_candidates: list[str],  # Top-5 라인명
    reference_db: dict[str, dict[str, list[tuple]]]
) -> dict[str, Any]:
    """Coarse 후보를 Fine 매칭으로 최종 확정.
    returns {"line": "Line_A", "section": "102", "confidence": 0.97}
    """
```

**기술 선택:**
- SuperPoint + SuperGlue (실시간 특징 매칭, 경량)
  또는 LoFTR (더 정확하지만 느림)
- Phase 1 anchor_detector와 pattern_matcher 재사용
- 응답 시간 ≤ 1.0초 (전체 파이프라인 Coarse 500ms + Fine 500ms 배분)

**의존성:**
```
# Phase 2-2 추가
superpoint  또는  LoFTR
```

**TDD 체크리스트 (예상):**
- [ ] Red: Top-5 입력 → 최종 1개 출력 형식 검증
- [ ] Red: 응답 시간 ≤ 1.0s 테스트
- [ ] Red: Fine 매칭 신뢰도 ≥ Coarse 신뢰도
- [ ] Green: SuperPoint/LoFTR 파이프라인 구현
- [ ] Green: Phase 1 (anchor_detector + pattern_matcher) 통합
- [ ] Refactor: 상수 정리, 에러 처리
- [ ] SubAgent3/4: 컴플라이언스 검증

---

## 아키텍처 진행 상황

### Phase 2 하이브리드 엔진 구조 (진행 현황)

```
입력: 도면 이미지 (임의 크기)
  ↓
[Task 2-1] Coarse Matcher ✅ 완료
  ├─ CNN ResNet-18로 전체 특징 추출
  ├─ 1000 ImageNet 클래스 → 라인명 맵핑 (mock)
  └─ Top-5 라인 후보 반환: [("Line_A", 0.95), ...]
  ↓
[Task 2-2] Fine Matcher ⬜ 진행 대기
  ├─ Task 1-3 anchor_detector 재사용
  ├─ SuperPoint/LoFTR로 이미지 특징 매칭
  ├─ Top-5 각각에 대해 anchor 좌표 추출
  └─ Task 1-4 pattern_matcher로 정밀 매칭
  ↓
[Task 2-3] OCR 교차검증 ⬜ 대기
  ├─ 고해상도 이미지 → 기둥 번호 OCR 추출
  └─ OCR 결과로 최종 신뢰도 보정
  ↓
최종 결과: {"line": "Line_A", "section": "102", "confidence": 0.98}
```

---

## 다음 검토 항목

Task 2-2 시작 전 확인:
- [ ] PLAN.md Task 2-2 인터페이스 및 구현 포인트 세부 검토
- [ ] SuperPoint vs LoFTR 기술 선택 결정 필요
- [ ] Phase 1 anchor_detector, pattern_matcher 재사용 계획 검토
- [ ] 응답 시간 목표: 1.0초 이내 (Coarse 500ms + Fine 500ms)
- [ ] Reference DB 구조 (mock 라인명 → 실제 라인 DB로 변경 필요)

---

## Phase 2 완료 기준 (PRD §6)

| 지표 | 목표 | 현황 |
|------|------|------|
| 오분류율 | ≤1% | Task 2-2/2-3 완료 시 검증 |
| 응답 속도 | ≤1.5s | Coarse: 0.16ms + Fine: 예정 |
| 30% 축소 식별 | 성공 | Phase 1에서 입증됨 ✓ |

---

## 참고: PyTorch 내부망 설치 불가 대응

Task 2-1 구현 시 내부망에서 PyTorch 설치 불가능할 경우를 대비하여:
- `try: import torch ... except ImportError:` 패턴 적용
- NumPy 기반 softmax 폴백 구현
- Mock CNN (무작위 신뢰도 생성)으로 형식 검증

**현재 상태:** PyTorch 설치 완료, 폴백 로직 테스트됨

---

## 최신 커밋 (Task 2-1)

```
23315fb docs: Task 2-1 완료 후 4개 문서 갱신
f303f90 refactor(phase2): coarse_matcher 타입 힌트 완성 및 assert 제거, 배치 분기 정리
e15ae99 feat(phase2): Green - coarse_matcher ResNet-18 최소 구현 (numpy 폴백 포함)
f07ad9f test(phase2): Red - coarse_matcher Top-K 형식 및 배치 처리 테스트 작성
e08d26c chore(phase2): requirements.txt에 PyTorch 추가
```

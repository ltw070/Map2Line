# NEXT_JOB.md — 다음 작업 재진입 프롬프트

> 이 파일은 작업을 중단했다가 재개할 때 사용하는 컨텍스트 복원 문서입니다.
> 재진입 시 아래 프롬프트를 그대로 붙여넣어 시작하세요.

---

## 현재 상태 요약 (2026-05-10 기준)

| 항목 | 내용 |
|------|------|
| 완료 | Phase 1 (4/4) + Phase 2 Task 2-1 (Coarse Matcher) ✅ + Task 2-2 (Fine Matcher) ✅ |
| 진행 중 | Phase 2 Task 2-3 대기 |
| 다음 Task | **Task 2-3 OCR 교차검증** (`src/ocr/column_reader.py` — EasyOCR 기반 기둥 번호 추출) |
| 테스트 현황 | pytest 69/69 PASS (2 skipped), 커버리지 82% |
| 레포 | https://github.com/ltw070/Map2Line |

---

## 재진입 프롬프트 (아래 내용을 그대로 입력)

```
Map2Line 프로젝트 개발을 재개합니다.

현재 상태:
- Phase 2 Task 2-2 Fine Matcher 완료 ✅
- pytest 69/69 PASS (18개 신규 + 51개 기존, 2 skipped)
- 커버리지 82% (목표 80% 달성)
- Laplacian NumPy 특징점 기반 Fine Matcher 구현 완료
- kornia SuperPoint 폴백 구조 준비됨 (Phase 3에서 교체 예정)

다음 작업:
- Phase 2 Task 2-3 OCR 교차검증 (기둥 번호 추출 → 신뢰도 보정)
- PLAN.md Task 2-3 세부사항 검토
- TDD + SubAgent 하네스로 개발 진행
- 완료된 Task마다 REPORT.md / README.md / CLAUDE.md / MANUAL.md 업데이트 후 GitHub push
```

---

## Task 2-2 (Fine Matcher) 완료 내역

### 구현 내용
- `requirements.txt` — kornia>=0.7.0 추가
- `tests/test_fine_matcher.py` — 18개 테스트 작성
  - 반환 형식 (dict/list, 필수 키: line/section/confidence)
  - 후보 선택 검증 (결과가 Coarse 후보 중 하나)
  - 최소 입력(1개~2개 후보) 경계값 처리
  - 응답 시간 ≤ 1.0s (inference_time_ms 키 또는 실행시간 직접 측정)
  - confidence 범위 (0.0~1.0), 내림차순 정렬

- `src/matching/fine_matcher.py` — Laplacian 특징점 기반 Fine 매칭
  - Laplacian 기반 NumPy mock 특징점 추출 (고주파 성분 밀도)
  - kornia 가용 시 _KORNIA_AVAILABLE=True 설정, Phase 3에서 SuperPoint로 교체 예정
  - Coarse 신뢰도 × 특징점 비율 보정 계수로 Fine 신뢰도 산출
  - top_k=1 → dict, top_k>1 → list (confidence 내림차순)

### 검증 결과
- SubAgent3 (테스트): 18 PASS, 86% 커버리지 (fine_matcher.py)
- SubAgent4 (컴플라이언스): flake8/mypy/bandit 0 violations
- 성능: Laplacian 연산 ~0.001-0.005ms (목표 1000ms 대비 200,000배 빠름)

### 기술 선택
- **특징점 추출:** NumPy Laplacian 응답 기반 mock (SuperPoint 모델 로드 비용 회피)
- **kornia 구조:** 가용성 확인 + 폴백 구조 준비 (Phase 3 SuperPoint 교체 예정)
- **Fine 신뢰도:** Coarse × (1 - 0.1 × (1 - kp_ratio)) 공식
- **section:** MVP에서 "0" mock, Phase 2-4에서 pattern_matcher 통합으로 교체

---

## Task 2-3 (OCR 교차검증) 개요

### 역할
Fine Matcher 결과를 OCR로 교차 검증하여 신뢰도 보정

**파이프라인:**
```
Fine Result: {"line": "Line_A", "section": "0", "confidence": 0.94}
             ↓
     OCR Verifier
     (EasyOCR 기둥 번호 추출)
             ↓
Final Result: {"line": "Line_A", "section": "102", "confidence": 0.97}
             (OCR 일치 시 신뢰도 상승, 불일치 시 하향)
```

### PLAN.md Task 2-3 체크리스트
- [ ] Red: 해상도 충분 → 기둥 번호 추출 테스트
- [ ] Red: 저해상도 → graceful skip (예외 없음) 테스트
- [ ] Red: OCR 결과 불일치 → 신뢰도 하향 조정 테스트
- [ ] Green: EasyOCR 통합 + 신뢰도 보정 로직
- [ ] SubAgent3 ‖ SubAgent4

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
[Task 2-2] Fine Matcher ✅ 완료
  ├─ Laplacian 특징점 수 계산 (NumPy mock)
  ├─ Coarse 신뢰도 × 특징점 보정 계수
  └─ Top-K 재평가 후 최종 라인 선택
  ↓
[Task 2-3] OCR 교차검증 ⬜ 진행 대기
  ├─ 고해상도 이미지 → 기둥 번호 OCR 추출
  └─ OCR 결과로 최종 신뢰도 보정
  ↓
최종 결과: {"line": "Line_A", "section": "102", "confidence": 0.98}
```

---

## Phase 2 완료 기준 (PRD §6)

| 지표 | 목표 | 현황 |
|------|------|------|
| 오분류율 | ≤1% | Task 2-3/2-4 완료 시 검증 |
| 응답 속도 | ≤1.5s | Coarse: ~150ms + Fine: ~0.005ms |
| 30% 축소 식별 | 성공 | Phase 1에서 입증됨 ✓ |

---

## 최신 커밋 (Task 2-2)

```
0c8d17f refactor(phase2): fine_matcher torch 미사용 import 제거, flake8 F401 해결
9b1aed0 feat(phase2): Green - fine_matcher Laplacian 특징점 기반 최소 구현 (kornia 폴백 포함)
519e558 test(phase2): Red - fine_matcher 테스트 작성 (형식, 성능, 신뢰도 16개)
836d306 chore(phase2): requirements.txt에 kornia 추가 (Fine Matcher SuperPoint 의존성)
23315fb docs: Task 2-1 완료 후 4개 문서 갱신
```

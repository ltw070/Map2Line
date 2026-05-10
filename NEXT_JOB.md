# NEXT_JOB.md — 다음 작업 재진입 프롬프트

> 이 파일은 작업을 중단했다가 재개할 때 사용하는 컨텍스트 복원 문서입니다.
> 재진입 시 아래 프롬프트를 그대로 붙여넣어 시작하세요.

---

## 현재 상태 요약 (2026-05-10 기준)

| 항목 | 내용 |
|------|------|
| 완료 | Phase 1 (4/4) + Phase 2 (4/4) — 전체 8개 Task 완료 |
| 진행 중 | Phase 3 진입 준비 |
| 다음 Task | **Task 3-1 스케일 불변성 강화** (멀티스케일 TTA + 앙상블) |
| 테스트 현황 | pytest 110/110 PASS (2 skipped), 커버리지 84% |
| 레포 | https://github.com/ltw070/Map2Line |

---

## 재진입 프롬프트 (아래 내용을 그대로 입력)

```
Map2Line 프로젝트 개발을 재개합니다.

현재 상태:
- Phase 2 모두 완료 ✅ (Task 2-1 Coarse / 2-2 Fine / 2-3 OCR / 2-4 FastAPI)
- pytest 110/110 PASS (2 skipped), 커버리지 84%
- POST /identify 엔드포인트 완전 동작 (Coarse→Fine→OCR 파이프라인 통합)
- fastapi 0.136.1 / uvicorn 0.46.0 설치 완료 (내부망 --trusted-host 방식)

다음 작업:
- Phase 3 Task 3-1 스케일 불변성 강화
- PLAN.md Task 3-1 세부사항 검토 (멀티스케일 TTA + 앙상블)
- TDD + SubAgent 하네스로 개발 진행
- 완료된 Task마다 REPORT.md / README.md / CLAUDE.md / MANUAL.md 업데이트 후 GitHub push
```

---

## Task 2-4 (FastAPI 엔드포인트) 완료 내역

### 구현 내용
- `requirements.txt` — fastapi, uvicorn[standard], python-multipart 추가
- `tests/test_api.py` — 16개 테스트 작성
  - TestIdentifyResponseFormat (8개): HTTP 200, 필수 키, 타입 검증
  - TestIdentifyResponseTime (3개): p95 ≤1.5s 성능 검증
  - TestIdentifyInvalidInput (5개): 422 에러 처리 검증

- `src/api/main.py` — FastAPI 엔드포인트 + 완전한 파이프라인 통합
  - `POST /identify`: multipart 이미지 수신 → Coarse → Fine → OCR → JSON 응답
  - `_validate_upload()`: Content-Type + 파일명 확장자 이중 검증
  - `_decode_image()`: numpy frombuffer + cv2.imdecode
  - `_run_pipeline()`: coarse_matcher → fine_matcher → verify_with_ocr 통합
  - `_estimate_columns()`: Phase 2 MVP mock (Phase 3에서 교체 예정)

### 검증 결과
- SubAgent3 (테스트): 16 PASS, 96% 커버리지 (api/main.py)
- SubAgent4 (컴플라이언스): flake8/mypy/bandit 0 violations
- 전체 커버리지: 84% (목표 80% 초과)
- 응답 시간: p95 < 300ms (목표 1500ms 대비 5배 이상 여유)

### 기술 선택
- **422 에러**: FastAPI 기본 422 (필드 누락) + 커스텀 422 (형식/디코딩 오류) 통합
- **columns 필드**: Phase 2 MVP에서 이미지 해상도 기반 mock, Phase 3 anchor_detector 통합 예정
- **파이프라인**: coarse_matcher (Top-5) → fine_matcher (top_k=1) → verify_with_ocr 직렬 실행
- **내부망 설치**: `pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org`

---

## 아키텍처 진행 상황

### Phase 2 하이브리드 엔진 구조 (완료)

```
입력: 도면 이미지 (임의 크기)
  ↓
[Task 2-1] Coarse Matcher ✅ 완료
  ├─ CNN ResNet-18로 전체 특징 추출
  └─ Top-5 라인 후보 반환
  ↓
[Task 2-2] Fine Matcher ✅ 완료
  ├─ Laplacian 특징점 수 계산 (NumPy mock)
  └─ Top-1 라인 선택
  ↓
[Task 2-3] OCR 교차검증 ✅ 완료
  ├─ EasyOCR 기둥 번호 추출 (미설치 시 graceful skip)
  └─ 신뢰도 보정 (+0.05 / -0.10)
  ↓
[Task 2-4] FastAPI 엔드포인트 ✅ 완료
  ├─ POST /identify 라우터
  └─ 전체 파이프라인 통합
  ↓
최종 결과: {"line": "Line_A_1", "section": "0", "confidence": 0.85, "columns": "L1-L5", ...}
```

---

## Phase 3 완료 기준 (PRD §6)

| 지표 | 목표 | 현황 |
|------|------|------|
| 오분류율 | ≤1% | Phase 3 스케일 테스트에서 검증 |
| 응답 속도 | ≤1.5s | 현재 p95 < 300ms ✓ |
| 30% 축소 식별 | 성공 | Phase 3 Task 3-1에서 검증 |

---

## Phase 진행도 정리

| Phase | 상태 | 진행도 | Task별 상태 |
|-------|------|--------|-----------|
| Phase 1 | ✅ 완료 | 4/4 | 1-1 ✅ / 1-2 ✅ / 1-3 ✅ / 1-4 ✅ |
| Phase 2 | ✅ 완료 | 4/4 | 2-1 ✅ / 2-2 ✅ / 2-3 ✅ / 2-4 ✅ |
| Phase 3 | ⬜ 대기 중 | 0/3 | 3-1 ⬜ / 3-2 ⬜ / 3-3 ⬜ |

---

## 최신 커밋 (Task 2-4)

```
390df01 refactor(phase2): api/main.py unused import 제거, 상수/타입힌트/에러메시지 정리
c13a364 feat(phase2): Green - FastAPI /identify 엔드포인트 최소 구현 (Coarse→Fine→OCR 파이프라인 통합)
21b93c8 test(phase2): Red - FastAPI /identify 엔드포인트 테스트 작성 (응답 형식/성능/에러 16개)
```

---

## 다음 검토 항목

Task 3-1 시작 전 확인:
- [ ] PLAN.md Task 3-1 인터페이스 및 구현 포인트 세부 검토
- [ ] 멀티스케일 TTA (Test-Time Augmentation) 전략 확정
- [ ] 스케일 테스트 fixture 설계 (20%, 30%, 50% 축소)
- [ ] TTA 앙상블 전략 (평균/최댓값/가중 평균)

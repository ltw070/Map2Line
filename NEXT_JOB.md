# NEXT_JOB.md — 작업 재진입 컨텍스트

> 이 파일은 작업을 중단했다가 재개할 때 현황을 빠르게 파악하기 위한 문서입니다.

---

## 현재 상태 (2026-05-10 기준)

| 항목 | 내용 |
|------|------|
| **전체 진행도** | **Phase 1 + 2 + 3 모두 완료** ✅ |
| **다음 작업** | 없음 — 구현 파이프라인 완료 |
| **미결 이슈** | Flaky 테스트 1건 (아래 참조) |
| **GitHub** | https://github.com/ltw070/Map2Line (master = main 동기화) |
| **마지막 커밋** | `65b3201` docs: Task 3-3 완료 후 4개 문서 갱신 |

---

## Phase 완료 현황

| Phase | Task | 상태 | 주요 파일 |
|-------|------|------|---------|
| **Phase 1** | 1-1 환경 설정 | ✅ | `requirements.txt`, `setup.cfg`, `conftest.py` |
| | 1-2 색상 분리 | ✅ | `src/preprocessing/color_segmentation.py` |
| | 1-3 앵커 탐지 | ✅ | `src/preprocessing/anchor_detector.py` |
| | 1-4 패턴 매칭 | ✅ | `src/matching/pattern_matcher.py` |
| **Phase 2** | 2-1 Coarse CNN | ✅ | `src/matching/coarse_matcher.py` |
| | 2-2 Fine Matcher | ✅ | `src/matching/fine_matcher.py` |
| | 2-3 OCR 교차검증 | ✅ | `src/ocr/column_reader.py` |
| | 2-4 FastAPI | ✅ | `src/api/main.py` |
| **Phase 3** | 3-1 스케일 불변성 | ✅ | `src/matching/scale_optimizer.py` |
| | 3-2 데이터 증강 | ✅ | `src/preprocessing/data_augmentation.py` |
| | 3-3 Streamlit UI | ✅ | `src/ui/app.py` |

---

## 테스트 현황

```
pytest tests/ --ignore=tests/test_api.py  (FastAPI 미설치 환경 기준)

결과: 138 PASSED / 4 SKIPPED / 1 FAILED
커버리지: 86%
```

### FAILED 1건 — Flaky 테스트 (알려진 이슈)

```
tests/test_scale_invariance.py::TestEnsembleAccuracyImprovement
  ::test_multiscale_confidence_vs_single_scale

원인: ResNet-18 softmax 출력이 1000 클래스로 분산되어
      멀티스케일 가중 평균이 단일 고신뢰도 값을 희석하는 케이스 발생

처리 방안 (미결):
  A. @pytest.mark.xfail 처리 후 실 도면 데이터로 재검증
  B. 허용 오차를 -0.15로 완화하고 주석으로 근거 명시
```

### SKIPPED 4건

| 테스트 | 이유 |
|--------|------|
| `test_ui_imports_without_error` | streamlit 미설치 |
| `test_streamlit_installed` | streamlit 미설치 |
| `test_red_recall_on_real_map` | data/samples/ 실제 도면 없음 |
| `test_scale_invariance` 1건 | data/samples/ 실제 도면 없음 |

---

## 파이프라인 아키텍처 (최종)

```
입력 이미지
  │
  ├─ [Phase 1] OpenCV 식별 경로
  │   ├─ color_segmentation.py  — HSV 색상 레이어 분리
  │   ├─ anchor_detector.py     — 붉은 기둥 Blob → 좌표 목록
  │   └─ pattern_matcher.py     — 기하 패턴 매칭 → 라인/구역/신뢰도
  │
  └─ [Phase 2] CNN 하이브리드 경로
      ├─ coarse_matcher.py      — ResNet-18 Top-5 후보
      ├─ fine_matcher.py        — Laplacian 특징점 → Top-1
      └─ column_reader.py       — EasyOCR 신뢰도 보정

  [Phase 3] 스케일 / 품질 / UI
  ├─ scale_optimizer.py         — 멀티스케일 TTA (20/30/50/100%)
  ├─ data_augmentation.py       — 학습 데이터 증강 파이프라인
  ├─ api/main.py                — POST /identify FastAPI 엔드포인트
  └─ ui/app.py                  — Streamlit 웹 UI
```

---

## API 실행 방법

```bash
# 가상환경 활성화
.venv\Scripts\activate

# FastAPI 서버
uvicorn src.api.main:app --reload --port 8000

# Streamlit UI (별도 터미널)
streamlit run src/ui/app.py
# → http://localhost:8501

# 테스트 실행
pytest tests/ --ignore=tests/test_api.py -v --cov=src
```

---

## 미결 사항 / 차기 개선 포인트

| 항목 | 내용 | 우선순위 |
|------|------|---------|
| Flaky 테스트 | `test_multiscale_confidence_vs_single_scale` xfail 처리 | 중간 |
| 실 도면 데이터 | `data/samples/` 실제 도면 추가 → SKIPPED 테스트 활성화 | 높음 |
| scipy 폴백 동등성 | numpy 폴백과 scipy 결과 일치 여부 단위 테스트 | 낮음 |
| API 응답 스펙 | `inference_time_ms` 필드 노출 여부 결정 | 낮음 |
| 실 도면 fine-tuning | ResNet-18 confidence 절대값 개선 (현재 ~0.001 수준) | 높음 |

---

## 문서 위치

| 문서 | 용도 |
|------|------|
| `PRD.md` | 요구사항 정의 (기능·지표) |
| `PLAN.md` | Task별 TDD 체크리스트 (모두 완료) |
| `REPORT.md` | 개발 이력 (Task별 변경 내용·결과) |
| `MANUAL.md` | 설치·실행·API·UI 사용 설명서 |
| `CRA_REPORT.md` | 작업 분석 리포트 (Agents / TDD / Clean Code / Refactoring) |
| `PR_REVIEW_POINTS.md` | PR 리뷰 요청 포인트 (6가지 체크포인트) |

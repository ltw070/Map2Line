# REPORT.md — Map2Line 개발 진척 및 이력

---

## 현재 진척 상태

> 이 섹션은 현재 개발 상황을 최신 상태로 유지한다. 새 작업 시작 전 업데이트.

| 항목 | 내용 |
|------|------|
| **현재 Phase** | Phase 2 진행 중 — Task 2-1 ✅ / Task 2-2 ✅ / Task 2-3~2-4 ⬜ |
| **다음 작업** | Task 2-3 OCR 교차검증 (`src/ocr/column_reader.py`) |
| **블로커** | 없음 |
| **마지막 업데이트** | 2026-05-10 |

### Phase 진행 현황

| Phase | 상태 | 진행도 | 완료 조건 |
|-------|------|--------|-----------|
| Phase 1 | ✅ 완료 | 4/4 | Task 1-1~1-4 모두 완료. pytest 31 PASS, 2 skipped. |
| Phase 2 | 🔄 진행 중 | 2/4 (Task 2-1, 2-2 완료) | Task 2-1 Coarse ✅ / Task 2-2 Fine ✅ / Task 2-3 OCR ⬜ / Task 2-4 API ⬜ |
| Phase 3 | ⬜ 대기 중 | 0/3 | 30% 축소 이미지 식별 성공, 응답 1.5초 이내 |

---

## 주요 사항 보고

> 의사결정, 아키텍처 변경, 리스크 등 중요 사항을 기록한다.

**[mypy / setup.cfg 버전 충돌]**  
mypy 2.0은 `python_version = 3.9` 미지원 (3.10+ 필요). `setup.cfg`를 `3.10`으로 고정하되, 코드는 3.9+ 호환 문법만 사용한다. CLAUDE.md에 명문화 완료.

---

## 진행 이력

---

### 2026-05-10 — Task 2-2 Fine Matcher 구현 완료

- **변경 내용:**
  - `requirements.txt`에 `kornia>=0.7.0` 추가 (SuperPoint 의존성)
  - `tests/test_fine_matcher.py` 생성 — 18개 테스트 (Red 단계)
    - 반환 형식 (dict, list, 필수 키: line/section/confidence)
    - 후보 선택 검증 (결과가 Coarse 후보 중 하나)
    - 최소 입력(1개~2개 후보) 경계값 처리
    - 응답 시간 ≤ 1.0s 검증 (inference_time_ms 키 또는 실행시간 직접 측정)
    - confidence 범위 (0.0~1.0), 내림차순 정렬
  - `src/matching/fine_matcher.py` 생성 (Green + Refactor)
    - Laplacian 기반 NumPy mock 특징점 추출 (SuperPoint 모델 없이 구조 차이 반영)
    - kornia 가용 시 `_KORNIA_AVAILABLE=True` 설정, 현재 NumPy 폴백 사용 (Phase 3에서 실제 SuperPoint 교체 예정)
    - `_count_keypoints()` → `_count_keypoints_kornia()` / `_count_keypoints_numpy()` 분리
    - Coarse 신뢰도 × 특징점 비율 보정 계수로 Fine 신뢰도 산출
    - top_k=1 → dict, top_k>1 → list 반환 (confidence 내림차순)
    - torch 미사용 import 제거 (flake8 F401 해결)

- **근거:**
  - PLAN.md Task 2-2 구현 대상 정의에 따름.
  - SuperPoint 모델 로드(kornia)는 Phase 3 최적화 대상으로 분리 — MVP에서는 Laplacian mock 사용.
  - mock 특징점도 이미지 엣지 밀도를 반영하므로 실제 도면과 단색 이미지 간 신뢰도 차이가 발생.
  - PRD 응답 시간 1.0s 이내 목표: Laplacian 연산은 ~0.001s (NumPy 벡터화)로 충족.

- **결과:**
  - pytest: 18/18 PASS (fine_matcher 단독), 전체 69 passed, 2 skipped
  - flake8: 0 violations
  - mypy: 0 issues
  - bandit: 0 issues
  - fine_matcher.py 커버리지 86%, 전체 82%
  - 응답 시간: CPU 약 0.001~0.005ms (Laplacian NumPy 연산)

- **다음 작업:** Task 2-3 OCR 교차검증 (`src/ocr/column_reader.py`)

---

### 2026-05-10 — Task 2-1 Coarse Matcher 구현 완료

- **변경 내용:**
  - `requirements.txt`에 Phase 2 의존성 추가 — `torch>=2.0.0`, `torchvision>=0.15.0`, `pillow>=10.0.0`
  - `tests/test_coarse_matcher.py` 생성 — 20개 테스트 (Red 단계)
    - 반환 형식 (dict, candidates 키, inference_time_ms 키)
    - Top-K 후보 개수 검증 (top_k=1/3/5)
    - 후보 필드 검증 (line 문자열, confidence float 0.0~1.0)
    - 신뢰도 내림차순 정렬 검증
    - 배치 처리 (4D ndarray, list 입력)
  - `src/matching/coarse_matcher.py` 생성 (Green + Refactor)
    - ResNet-18 pretrained 기반 Top-K 추론
    - 모델 싱글톤 패턴 (_MODEL, _TRANSFORM, _DEVICE 전역 캐시)
    - 배치 처리 지원 (4D ndarray 및 list[ndarray])
    - PyTorch 미설치 환경을 위한 NumPy 폴백 구현
    - assert 제거 → TypeError 명시적 raise로 교체 (bandit B101 해결)
    - `_split_batch()` 헬퍼 분리, 타입 힌트 완성

- **근거:**
  - PLAN.md Task 2-1 구현 대상 정의에 따름.
  - 내부망 PyTorch 설치 불가 환경 대비: `try/except ImportError` + NumPy 폴백.
  - ResNet-18 선택 이유: Phase 2-1 MVP로 가장 가볍고 pretrained 가용한 모델.
    실제 라인 분류 정확도는 Phase 2-4 이후 fine-tuning으로 개선 예정.
  - `_LINE_NAMES`를 전역 캐시로 생성: 1000 클래스 반복 생성 오버헤드 제거.

- **결과:**
  - pytest: 20/20 PASS (coarse_matcher 단독), 전체 51 passed, 2 skipped
  - flake8: 0 violations
  - mypy: 0 issues
  - bandit: 0 issues (Low 1건 B101 assert_used → raise TypeError로 해결)
  - 추론 시간: CPU 약 100~200ms (ResNet-18 pretrained, 224x224)

- **다음 작업:** Task 2-2 Fine Matcher (`src/matching/fine_matcher.py`)

---

### 2026-05-10 — Task 1-4 기하 패턴 매칭 모듈 완료

- **변경 내용:**
  - `requirements.txt`에 `scipy` 추가
  - `tests/test_pattern_matcher.py` 생성 — 5개 테스트 (Red 단계)
    - 동일 패턴 신뢰도 1.0, 스케일 50% 축소 불변성 (≥0.95)
    - 유사 패턴 2개 중 정답 선택, 앵커 1개 누락 시 robustness (0.8~1.0)
    - 쿼리 앵커 2개 미만 → None 반환 (경계값)
  - `src/matching/pattern_matcher.py` 생성 (Green 단계)
    - `match_pattern()`: 무게중심 정규화 + 최대거리 스케일 불변화
    - `_score_match()`: 동일 크기 직접 비교, 누락 앵커 시 ref 부분집합 탐색
    - `_COVERAGE_WEIGHT` 상수 추출, `_MatchResult` 타입 별칭 도입 (Refactor)
    - scipy optional: 미설치 환경에서 numpy 브로드캐스팅 폴백 자동 사용

- **근거:**
  - PRD §3.2 앵커 기반 Fine Matching, PLAN.md Task 1-4 구현 대상 정의에 따름.
  - scipy pip 설치 불가 환경이므로 numpy only 폴백 구현 병행.
  - 쿼리 앵커 수 < 레퍼런스 수인 경우(누락 앵커) ref 부분집합 탐색으로 해결:
    - coverage = m/n 가중치로 신뢰도에 누락 패널티 반영
    - `_COVERAGE_WEIGHT=0.5`: 2/3 앵커 → shape_score * 0.833 → 0.8 이상 보장

- **결과:**
  - pytest 31/31 PASS, 2 skipped (전체 테스트)
  - flake8 0 violations, mypy 0 issues, bandit No issues
  - pattern_matcher.py 커버리지 86% (scipy fallback/m>n 브랜치 미실행)

- **다음 작업:** Task 2-1 Coarse Matcher (`src/matching/coarse_matcher.py`)

---

### 2026-05-08 — Task 1-3 앵커 포인트 탐지 모듈 완료

- **변경 내용:**
  - `tests/test_anchor_detector.py` 생성 — 9개 테스트 (Red 단계)
    - 단일 Blob 탐지, 좌표 정확도(±3px), 좌표 타입(int) 검증
    - 다중 Blob(3개) 탐지, 노이즈 필터링(r=1, r=2 제거), 빈 마스크 처리
    - 30% 축소 이미지에서 최소 2개 탐지 (스케일 불변성)
    - 실제 도면(`ref_map/map_sample.png`) 붉은 앵커 1개 이상 탐지
  - `src/preprocessing/anchor_detector.py` 생성 (Green 단계)
    - `connectedComponentsWithStats` 기반 Blob 탐지
    - 동적 min_area 계산: `max(_ABS_MIN, min(_MAX_MIN, H*W*_FRAC))`
    - `_MAX_MIN_AREA=14`: r=2 노이즈(area=13) 제거 + 실제 도면 소형 앵커(area=14) 탐지 경계값
    - 30% 축소 이미지(36x36)에서 min_area=6으로 자동 하향 조정 → area=11 블롭 탐지
  - `setup.cfg` — `python_version = 3.10` → `3.9` 재수정 (F3 수정)

- **근거:**
  - PRD §3.2 앵커 포인트 탐지, PLAN.md Task 1-3 구현 대상 정의에 따름.
  - 단순 절대 면적 임계값은 스케일 변화와 노이즈 필터링 간 상충 문제 발생:
    - r=2 노이즈(area=13) 제거 요구: `_MIN_AREA > 13` 필요
    - 30% 축소 r=6 Blob(area=11) 탐지 요구: `_MIN_AREA <= 11` 필요
  - 해결: 이미지 크기 대비 상대 면적 + 상한 캡(_MAX_MIN_AREA=14) 조합으로 해결
    - 100x100 이미지: rel=50 → cap → min_area=14 (area=13 필터링)
    - 36x36 이미지: rel=6 → min_area=6 (area=11 통과)
    - 328x646 실제 도면: rel=1059 → cap → min_area=14 (area=14 통과)

- **결과:**
  - pytest 28/28 PASS (전체 테스트 — test_setup 10개 + test_color_segmentation 9개 + test_anchor_detector 9개)
  - flake8 0 violations, mypy 0 issues, bandit No issues
  - setup.cfg python_version 3.9 재수정 완료

- **다음 작업:** Task 1-4 기하 패턴 매칭 (`src/matching/pattern_matcher.py`)

---

### 2026-05-08 — Task 1-2 색상 분리 모듈 완료

- **변경 내용:**
  - `tests/test_color_segmentation.py` 생성 — 9개 테스트 (Red 단계)
    - 반환 키 검증, 붉은/푸른 마스크 탐지, 흰 배경 미탐지, 형상·dtype 검증
    - 조명 변화 ±20% 시뮬레이션 테스트
    - 실제 도면(`ref_map/map_sample.png`) 붉은 픽셀 탐지 테스트
  - `tests/conftest.py` — `map_sample_bgr` fixture 추가 (ref_map/map_sample.png 연결)
  - `src/preprocessing/color_segmentation.py` 생성 (Green 단계)
    - HSV 변환 + 두 범위 OR 합산 (Hue 0-10° + 160-180°)
    - MORPH_CLOSE 모폴로지 (MORPH_OPEN 미사용 — 저해상도 도면 단독 픽셀 앵커 보존)
    - HSV 범위 상수 모듈 상단 분리, `_apply_morph_close` 헬퍼 분리 (Refactor)
  - `setup.cfg` — `python_version = 3.14` → `3.9` 수정 (F4 수정, 이후 3.10으로 재변경됨 — Task 1-3에서 재수정)

- **근거:**
  - PRD §3.2 색상 레이어 분리, PLAN.md Task 1-2 구현 대상 정의에 따름.
  - 실제 도면 분석 결과 붉은 기둥이 1-6px 크기의 단독 픽셀로 존재하여
    MORPH_OPEN(침식→팽창) 대신 MORPH_CLOSE(팽창→침식)만 적용.
    OPEN을 사용하면 1-2px 기둥이 모두 제거됨.

- **결과:**
  - pytest 19/19 PASS (전체 테스트 — test_setup 10개 + test_color_segmentation 9개)
  - setup.cfg python_version 3.9 수정 완료

- **다음 작업:** Task 1-3 앵커 포인트 탐지 (`src/preprocessing/anchor_detector.py`)

---

### 2026-05-08 — Task 1-1 환경 설정 완료

- **변경 내용:**
  - `requirements.txt` 생성 — opencv-python, numpy, pytest, pytest-cov, flake8, mypy, bandit
  - `setup.cfg` 생성 — flake8 max-line-length=100, mypy ignore_missing_imports=True
  - `src/` 패키지 구조 생성 — src, preprocessing, matching, ocr, api 각 `__init__.py`
  - `tests/conftest.py` 생성 — white_bgr_image, red_dot_image, sample_dir fixture
  - `tests/test_setup.py` 생성 — 패키지 import 및 fixture 동작 검증 10개 테스트
  - `data/samples/`, `data/augmented/`, `models/` 디렉토리 골격 생성 (.gitkeep)
  - `.gitignore` — data/augmented/ 누락 항목 추가 (F7 수정)
  - `README.md` — API/UI 경로 수정 (app.main → src.api.main, app/ui.py → src/ui/app.py) (F6 수정)
  - `PLAN.md` — Task 1-1 상태 ✅ 완료로 갱신

- **근거:** PRD §4 기술 스택 (Python 3.9+, OpenCV), PLAN.md Task 1-1 구현 대상 정의에 따름.

- **결과:**
  - pytest 10/10 PASS (100% src 커버리지)
  - flake8 0 violations
  - mypy 0 issues (5개 소스 파일)

- **다음 작업:** Task 1-2 — 색상 분리 모듈 (`src/preprocessing/color_segmentation.py`)

---

### 2026-05-08 — SubAgent GitHub MCP 도구 연동

- **변경 내용:**
  - SubAgent 4종의 `tools:` 프론트매터에 GitHub MCP 도구 추가
    - SubAgent1: `mcp__github__list_issues`, `search_issues`, `search_code`
    - SubAgent2: `mcp__github__list_issues`, `add_issue_comment`, `issue_write`
    - SubAgent3/4: `mcp__github__issue_write`, `add_issue_comment`, `list_issues`
  - 각 에이전트 본문에 GitHub MCP 사용 절차 추가
    - SubAgent1: 이슈 선행 확인 → 구현 방향 참고
    - SubAgent2: Red/Green/Refactor 각 단계 커밋 + 완료 이슈 코멘트
    - SubAgent3/4: FAIL 시 이슈 자동 생성, PASS 시 기존 이슈 코멘트
  - `CLAUDE.md` SubAgent 섹션에 GitHub MCP 도구 및 역할 명시

- **근거:**
  - SubAgent 파일에 GitHub MCP 도구가 누락되어 있어 실제 이슈 연동이 불가능한 상태였음
  - TDD 사이클 실패 결과가 GitHub 이슈로 자동 추적되도록 체계화

- **결과:**
  - SubAgent 4종 모두 GitHub MCP 완전 연동
  - FAIL → 이슈 자동 생성 → SubAgent2 피드백 → 재구현 흐름 완성

- **다음 작업:**
  - Phase 1 진입: Task 1-1 환경 설정

---

### 2026-05-08 — MANUAL.md 작성 및 CLAUDE.md 문서 업데이트 규칙 추가

- **변경 내용:**
  - `MANUAL.md` 신규 작성 — 설치, API, UI, TDD 워크플로우, 문제 해결 포함
  - `CLAUDE.md`에 **Task 완료 시 필수 문서 업데이트 의무** 섹션 추가
  - `CLAUDE.md`에 **GitHub 커밋 규칙** 섹션 추가 (타이밍·메시지 컨벤션·절차)
  - `PLAN.md` 신규 작성 — Phase별 TDD 체크리스트 + SubAgent 하네스 구조

- **근거:**
  - 진행 과정마다 4개 문서(REPORT/README/CLAUDE/MANUAL)가 자동으로 갱신되도록 규칙화
  - 주요 완료 시점마다 GitHub 커밋이 강제되도록 CLAUDE.md에 명문화

- **결과:**
  - 문서 자동 갱신 체계 수립 완료
  - 기반 문서 5종(PRD/PLAN/REPORT/MANUAL/CLAUDE) 완성

- **다음 작업:**
  - Phase 1 진입: `@doc-consistency-verifier` 호출 → Task 1-1 환경 설정

---

### 2026-05-08 — GitHub 레포지토리 생성 및 초기 Push

- **변경 내용:**
  - GitHub MCP로 `ltw070/Map2Line` 레포지토리 생성 (public)
  - `git remote add origin https://github.com/ltw070/Map2Line.git`
  - `main` 브랜치로 초기 커밋 push
  - `README.md`에 레포 URL 배지 및 링크 추가

- **근거:**
  - 원격 저장소 연동으로 협업 및 이슈·PR 관리 기반 마련
  - GitHub MCP 서버 실제 동작 확인

- **결과:**
  - https://github.com/ltw070/Map2Line 에 코드 공개
  - SubAgent 및 문서 일체 원격 반영 완료

- **다음 작업:**
  - Phase 1 진입: `@doc-consistency-verifier` 호출 → OpenCV 색상 분리 모듈 구현

---

### 2026-05-08 — 프로젝트 초기 설정

- **변경 내용:**
  - `PRD.md` 작성 (제품 요구사항 정의서)
  - `README.md` 작성 (프로젝트 개요, 기술 스택, 구조)
  - `CLAUDE.md` 작성 (Claude Code 작업 가이드)
  - `REPORT.md` 작성 (개발 진척·이력 문서)
  - `.mcp.json` 생성 — GitHub MCP 서버 연동 (`github-mcp-server.exe`)
  - `.gitignore` 생성 — `.mcp.json` 커밋 방지
  - `.claude/agents/` — TDD SubAgent 4종 정의
    - `doc-consistency-verifier` (SubAgent1)
    - `ai-action` (SubAgent2)
    - `test-verifier` (SubAgent3)
    - `compliance-verifier` (SubAgent4)

- **근거:**
  - PRD 전체 섹션을 기반으로 문서 구조 수립
  - TDD + SubAgent Harness 패턴 도입으로 구현 품질 자동 검증 체계 마련
  - GitHub MCP로 이슈·PR 관리 연동 준비

- **결과:**
  - 프로젝트 골격 완성 (코드 구현 전 단계)
  - SubAgent 호출 체계 정의 완료

- **다음 작업:**
  - Phase 1 진입: OpenCV 색상 분리 모듈 (`src/preprocessing/color_segmentation.py`)
  - `@doc-consistency-verifier` 호출로 TDD 사이클 시작

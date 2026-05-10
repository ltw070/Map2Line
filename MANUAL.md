# MANUAL.md — Map2Line 사용 설명서

> 이 문서는 Map2Line 시스템의 설치, 실행, 개발 워크플로우를 설명합니다.  
> 코드 변경이 생길 때마다 이 문서도 함께 최신 상태로 유지합니다.

---

## 목차

1. [환경 설치](#1-환경-설치)
2. [빠른 시작](#2-빠른-시작)
3. [API 사용법](#3-api-사용법)
4. [UI 사용법](#4-ui-사용법)
5. [개발 워크플로우 (TDD + SubAgent)](#5-개발-워크플로우-tdd--subagent)
6. [테스트 실행](#6-테스트-실행)
7. [코드 품질 검사](#7-코드-품질-검사)
8. [레퍼런스 DB 관리](#8-레퍼런스-db-관리)
9. [문제 해결](#9-문제-해결)

---

## 1. 환경 설치

### 전제 조건

| 항목 | 버전 |
|------|------|
| Python | 3.9 이상 |
| Git | 최신 |
| (선택) CUDA | GPU 추론 가속 시 필요 |

### 설치 순서

```bash
# 1. 저장소 클론
git clone https://github.com/ltw070/Map2Line.git
cd Map2Line

# 2. 가상환경 생성
python -m venv .venv

# 3. 가상환경 활성화 (Windows)
.venv\Scripts\activate

# 4. 의존성 설치
pip install -r requirements.txt
```

> **Windows PowerShell** 사용 시 `activate` 실행 오류가 나면:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

---

## 2. 빠른 시작

> Phase 1이 완료되어 패턴 매칭 코어 기능을 직접 사용할 수 있습니다.
> Phase 2-1 Coarse Matcher가 구현되어 CNN 기반 Top-K 후보 추출이 가능합니다.
> API 서버(Phase 2-4)는 아직 구현 중입니다.

```bash
# 가상환경 활성화
.venv\Scripts\activate

# API 서버 실행
uvicorn src.api.main:app --reload --port 8000

# 다른 터미널에서 테스트 요청
curl -X POST http://localhost:8000/identify \
  -F "image=@/path/to/floor_plan_crop.jpg"
```

**응답 예시:**
```json
{
  "line": "A",
  "section": "102",
  "columns": "B4-B6",
  "confidence": 0.97
}
```

---

## 3. API 사용법

### `POST /identify`

도면 이미지 조각을 업로드하면 라인명과 구역 정보를 반환합니다.

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `image` | file | ✅ | JPEG/PNG 이미지 |

**응답 필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `line` | string | 라인명 (예: `"A"`) |
| `section` | string | 구역 번호 (예: `"102"`) |
| `columns` | string | 기둥 범위 (예: `"B4-B6"`) |
| `confidence` | float | 신뢰도 0.0 ~ 1.0 |

**오류 응답:**

| HTTP | 의미 |
|------|------|
| 422 | 이미지 파일 형식 오류 |
| 500 | 서버 내부 오류 |

**Python 호출 예시:**
```python
import requests

with open("floor_crop.jpg", "rb") as f:
    res = requests.post(
        "http://localhost:8000/identify",
        files={"image": f},
    )
print(res.json())
```

---

## 4. UI 사용법

> Phase 3 완료 후 사용 가능합니다.

```bash
streamlit run src/ui/app.py
```

브라우저에서 `http://localhost:8501` 접속 후:

1. **이미지 업로드** — 도면 캡처 이미지(JPEG/PNG) 선택
2. **식별 실행** — "Identify" 버튼 클릭
3. **결과 확인** — 라인명, 구역, 신뢰도 표시
4. **앵커 오버레이** — 탐지된 붉은 기둥 위치를 이미지 위에 시각화

---

## 5. 개발 워크플로우 (TDD + SubAgent)

모든 기능 구현은 아래 4단계 SubAgent 사이클로 진행합니다.

### 사이클 개요

```
Step 1: @doc-consistency-verifier  — PRD ↔ 코드 정합성 확인
Step 2: @ai-action                 — Red → Green → Refactor
Step 3: @test-verifier             — pytest 검증        ┐ 병렬
        @compliance-verifier       — flake8/mypy/bandit  ┘
```

### Step 1 — 문서 정합성 확인

새 Task를 시작하기 전, PRD와 현재 코드 간 불일치를 탐지합니다.

```
Claude Code 프롬프트 예시:
"Task 1-2 색상 분리 모듈 구현을 시작합니다. @doc-consistency-verifier를 호출해주세요."
```

출력 예시:
```
PASS: PRD §3.2 색상 분리 요구사항 정의 존재
FAIL: src/preprocessing/color_segmentation.py 미구현
→ SubAgent2 우선 구현 항목: color_segmentation.py
```

### Step 2 — TDD 구현 (@ai-action)

```
[Red]    실패하는 테스트 먼저 작성
         → pytest 실행 → FAIL 확인
[Green]  최소한의 코드로 테스트 통과
         → pytest 실행 → PASS 확인
[Refactor] 중복 제거, 가독성 개선
         → pytest 재실행 → 여전히 PASS
```

### Step 3 — 검증 (병렬 실행)

SubAgent3과 SubAgent4를 동시에 호출합니다:

```
@test-verifier       → pytest + 커버리지 측정
                       FAIL 시 GitHub 이슈 자동 생성
@compliance-verifier → flake8 + mypy + bandit
                       HIGH 위반 시 GitHub 이슈 즉시 생성
```

둘 다 PASS → 다음 Task  
FAIL 존재 → @ai-action 재호출 (피드백 반영)  
GitHub 이슈에 FAIL 원인 자동 기록 → 추적 가능

### Task 완료 후 필수 작업

모든 Task가 완료되면 아래 4개 문서를 반드시 업데이트합니다:

```
1. REPORT.md  — 변경 내용, 근거, 결과, 다음 작업 기록
2. README.md  — 기능 상태(로드맵 테이블) 및 사용법 갱신
3. CLAUDE.md  — 새로운 컨벤션·규칙 발생 시 반영
4. MANUAL.md  — 사용자 관점 변경사항 반영
```

이후 GitHub 커밋:
```bash
git add .
git commit -m "feat(phase1): Task 1-2 색상 분리 모듈 구현"
git push
```

---

## 6. 테스트 실행

```bash
# 전체 테스트
pytest tests/ -v

# 커버리지 포함
pytest tests/ -v --cov=src --cov-report=term-missing

# 특정 모듈만
pytest tests/test_color_segmentation.py -v

# 빠른 연기 테스트 (smoke test)
pytest tests/ -v -x --tb=short
```

**커버리지 목표:** 각 모듈 ≥ 80%

---

## 7. 코드 품질 검사

```bash
# 린팅
flake8 src/ tests/ --max-line-length=100

# 타입 검사
mypy src/ --ignore-missing-imports

# 보안 취약점 검사
bandit -r src/ -ll

# 전체 한번에 실행
flake8 src/ tests/ --max-line-length=100 && \
mypy src/ --ignore-missing-imports && \
bandit -r src/ -ll
```

---

## 8. 레퍼런스 DB 관리

레퍼런스 DB는 각 라인의 앵커(기둥) 좌표 목록을 저장합니다.

> Phase 1 구현 후 실제 형식이 확정됩니다. 현재는 설계 단계입니다.

**확정 구조 (`data/reference_db.json`):**
```json
{
  "Line_A": {
    "section_102": [[120, 340], [250, 340], [380, 340]],
    "section_103": [[120, 480], [250, 480], [380, 480]]
  },
  "Line_B": {
    "section_201": [[115, 335], [248, 335], [375, 335]]
  }
}
```

**Python에서 직접 사용 — 패턴 매칭 (Phase 1 완료):**
```python
from src.matching.pattern_matcher import match_pattern

ref_db = {
    "Line_A": {
        "section_102": [(120, 340), (250, 340), (380, 340)],
    }
}
query_anchors = [(120, 340), (250, 340), (380, 340)]
result = match_pattern(query_anchors, ref_db)
# {"line": "Line_A", "section": "section_102", "confidence": 1.0}
```

**Python에서 직접 사용 — Coarse Matcher (Phase 2-1 완료):**
```python
import numpy as np
from src.matching.coarse_matcher import coarse_matcher

# 단일 이미지 (H, W, 3) BGR
image = np.random.randint(0, 256, (224, 224, 3), dtype=np.uint8)
result = coarse_matcher(image, top_k=5)
# {
#   "candidates": [{"line": "Line_A_1", "confidence": 0.023}, ...],
#   "inference_time_ms": 142.3
# }

# 배치 처리 (N, H, W, 3)
batch = np.random.randint(0, 256, (4, 224, 224, 3), dtype=np.uint8)
results = coarse_matcher(batch, top_k=5)  # list[dict], 길이=4
```

> **주의:** Phase 2-1 MVP에서 라인명은 ImageNet 클래스 인덱스 기반 Mock 값입니다.
> 실제 라인 분류는 Phase 2 fine-tuning 이후 정확해집니다.

**새 도면 등록 절차 (Phase 1 완료 후):**
```bash
python scripts/register_floor_plan.py \
  --image data/raw/line_a_section102.jpg \
  --line A \
  --section 102
```

---

## 9. 문제 해결

### 가상환경 활성화 안 됨 (Windows)

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.venv\Scripts\Activate.ps1
```

### OpenCV 임포트 오류

```bash
pip uninstall opencv-python opencv-python-headless
pip install opencv-python
```

### pytest 수집 오류

```bash
# conftest.py 경로 확인
pytest --co -q
```

### mypy 오류 `Module not found`

`setup.cfg`에 아래 설정이 있는지 확인:
```ini
[mypy]
ignore_missing_imports = True
```

---

> 요구사항 상세 → [PRD.md](./PRD.md) | 구현 계획 → [PLAN.md](./PLAN.md) | 개발 이력 → [REPORT.md](./REPORT.md)

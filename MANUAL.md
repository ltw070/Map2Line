# MANUAL.md — Map2Line 사용 설명서

반도체 공장 도면 이미지를 업로드하면 **어떤 라인의 어느 구역인지 자동으로 식별**해 주는 시스템입니다.

---

## 목차

1. [설치](#1-설치)
2. [빠른 시작](#2-빠른-시작)
3. [UI 사용법](#3-ui-사용법)
4. [API 사용법](#4-api-사용법)
5. [레퍼런스 DB 등록](#5-레퍼런스-db-등록)
6. [문제 해결](#6-문제-해결)

---

## 1. 설치

### 요구 사항

| 항목 | 버전 |
|------|------|
| Python | 3.9 이상 |
| Git | 최신 |
| CUDA | 선택 — GPU 가속 시 필요 |

### 설치 순서

```bash
# 1. 저장소 클론
git clone https://github.com/ltw070/Map2Line.git
cd Map2Line

# 2. 가상환경 생성 및 활성화
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux

# 3. 의존성 설치
pip install -r requirements.txt
```

> **Windows PowerShell에서 활성화가 안 되면:**
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

---

## 2. 빠른 시작

서버 2개를 각각 다른 터미널에서 실행합니다.

```bash
# 터미널 1 — API 서버
.venv\Scripts\activate
uvicorn src.api.main:app --reload --port 8000

# 터미널 2 — 웹 UI
.venv\Scripts\activate
streamlit run src/ui/app.py
```

브라우저에서 `http://localhost:8501` 접속 → 도면 이미지 업로드 → 결과 확인

---

## 3. UI 사용법

### 화면 구성

| 영역 | 설명 |
|------|------|
| 메인 업로드 영역 | 도면 이미지 드래그·드롭 또는 파일 선택 |
| 이미지 미리보기 | 업로드된 이미지와 해상도 표시 |
| 결과 패널 | 라인, 구역, 신뢰도, 응답 시간 |
| 상세 정보 | 기둥 좌표, 원본 JSON (접기/펼치기) |
| 사이드바 | API 서버 주소 설정 |

### 사용 절차

**1단계 — 이미지 업로드**

- 지원 형식: JPG, JPEG, PNG
- 최대 크기: 10MB
- 부분 캡처, 축소 이미지, 조명 변화가 있는 사진 모두 가능

**2단계 — 식별 실행**

- "API 호출 및 분석" 버튼 클릭
- 통상 100~300ms 내 결과 반환

**3단계 — 결과 확인**

| 항목 | 설명 | 예시 |
|------|------|------|
| 라인(Line) | 식별된 라인명 | `Line_A` |
| 구역(Section) | 구역 번호 | `102` |
| 신뢰도 | 식별 정확도 (높을수록 신뢰) | `97.3%` |
| 응답시간 | 서버 처리 시간 | `148ms` |

신뢰도가 낮을 경우 이미지 해상도를 높이거나 더 넓은 범위를 캡처해 재시도하세요.

### API 서버 주소 변경

사이드바 "⚙️ 설정" 에서 API 주소 입력:

```
기본값: http://localhost:8000
원격 서버: http://192.168.1.100:8000
```

### 에러 메시지 안내

| 메시지 | 원인 | 해결 방법 |
|--------|------|---------|
| "API 서버에 연결할 수 없습니다" | FastAPI 서버 미실행 또는 주소 오류 | 터미널 1에서 `uvicorn src.api.main:app --reload` 실행 |
| "API 요청 시간 초과" | 서버 응답 30초 초과 | 이미지 크기 축소 후 재시도 |
| "응답 파싱 오류" | API 응답 포맷 오류 | 서버 로그 확인 |
| 파일 업로드 불가 | 지원하지 않는 형식 또는 10MB 초과 | JPG/PNG, 10MB 이하로 변환 후 재시도 |

---

## 4. API 사용법

UI 없이 코드에서 직접 호출할 때 사용합니다.

### POST /identify

```
URL:  POST http://localhost:8000/identify
Body: multipart/form-data  (image: 파일)
```

**curl 예시:**

```bash
curl -X POST http://localhost:8000/identify \
  -F "image=@/path/to/floor_plan_crop.jpg"
```

**Python 예시:**

```python
import requests

with open("floor_plan_crop.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8000/identify",
        files={"image": f},
    )
print(response.json())
```

**응답:**

```json
{
  "line":       "Line_A",
  "section":    "102",
  "columns":    "B4-B6",
  "confidence": 0.97,
  "inference_time_ms": 148.3
}
```

**응답 필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `line` | string | 식별된 라인명 |
| `section` | string | 구역 번호 |
| `columns` | string | 기둥 범위 |
| `confidence` | float | 신뢰도 0.0 ~ 1.0 |
| `inference_time_ms` | float | 처리 시간 (ms) |

**오류 응답:**

| HTTP 상태 | 의미 |
|-----------|------|
| 422 | 이미지 형식 오류 (JPEG/PNG 아님, 빈 파일, 손상된 파일) |
| 500 | 서버 내부 오류 |

### 멀티스케일 추론 직접 호출 (Python)

캡처 품질이 낮거나 이미지가 30% 이하로 축소된 경우 권장합니다.

```python
import cv2
from src.matching.scale_optimizer import multiscale_inference

image = cv2.imread("floor_plan_crop.jpg")
result = multiscale_inference(image)

print(result["line"])               # "Line_A"
print(f'{result["confidence"]:.1%}') # "92.0%"
print(result["inference_time_ms"])  # 1200.0

# 스케일별 상세 결과
for r in result["scale_results"]:
    print(f'  {int(r["scale"]*100)}% 축소: {r["line"]} ({r["confidence"]:.2f})')
```

---

## 5. 레퍼런스 DB 등록

Map2Line은 **사전에 등록된 도면 좌표 데이터(레퍼런스 DB)**와 쿼리 이미지를 비교하여 라인을 식별합니다.
새 라인·구역을 식별 대상에 추가하려면 아래 절차로 등록합니다.

### DB 형식

`data/reference_db.json`

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

- 최상위 키: 라인명
- 두 번째 키: 구역명
- 값: 해당 구역 도면에서의 기둥(앵커) 픽셀 좌표 목록 `[x, y]`

### 등록 절차

1. 등록할 라인·구역의 **원본 도면 이미지**를 준비합니다.
2. 도면에서 붉은 기둥의 픽셀 좌표 `[x, y]`를 수집합니다.
   - 이미지 편집 툴(예: GIMP, Photoshop)에서 픽셀 위치 확인 가능
   - 또는 `detect_anchors()`로 자동 추출 가능 (아래 참고)
3. `data/reference_db.json`에 해당 라인·구역 항목을 추가합니다.

**자동 좌표 추출 (Python):**

```python
import cv2
from src.preprocessing.color_segmentation import segment_colors
from src.preprocessing.anchor_detector import detect_anchors

image = cv2.imread("data/raw/line_a_section102.jpg")
masks = segment_colors(image)
anchors = detect_anchors(masks["red"])

print(anchors)
# [(120, 340), (250, 340), (380, 340)]
```

추출된 좌표를 `reference_db.json`에 복사하면 등록 완료입니다.

### 등록 확인

```python
from src.matching.pattern_matcher import match_pattern
import json

with open("data/reference_db.json") as f:
    ref_db = json.load(f)

# 알려진 앵커 좌표로 테스트
query = [(120, 340), (250, 340), (380, 340)]
result = match_pattern(query, ref_db)
print(result)
# {"line": "Line_A", "section": "section_102", "confidence": 1.0}
```

---

## 6. 문제 해결

### 가상환경 활성화 안 됨 (Windows)

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.venv\Scripts\Activate.ps1
```

### pip install 실패 (내부망 환경)

```bash
pip install -r requirements.txt \
  --trusted-host pypi.org \
  --trusted-host files.pythonhosted.org
```

### OpenCV 임포트 오류

```bash
pip uninstall opencv-python opencv-python-headless
pip install opencv-python
```

### 서버 시작 오류 — `ModuleNotFoundError`

프로젝트 루트 디렉토리에서 실행하고 있는지 확인:

```bash
cd Map2Line
uvicorn src.api.main:app --reload --port 8000
```

### 식별 결과 신뢰도가 낮을 때

| 원인 | 해결 방법 |
|------|---------|
| 이미지 너무 작음 (30% 미만) | 원본 이미지 또는 더 큰 캡처 범위 사용 |
| 기둥이 잘려서 보이지 않음 | 기둥이 포함된 범위로 다시 캡처 |
| 해당 라인이 DB에 미등록 | §5 레퍼런스 DB 등록 절차 수행 |
| 조명이 매우 어둡거나 과노출 | 이미지 밝기 보정 후 재시도 |

---

> 요구사항 → [PRD.md](./PRD.md) | 개발 이력 → [REPORT.md](./REPORT.md) | 리뷰 포인트 → [PR_REVIEW_POINTS.md](./PR_REVIEW_POINTS.md)

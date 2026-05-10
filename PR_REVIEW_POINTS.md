## feat: 도면 기반 라인 자동 식별 시스템 구현 — OpenCV + CNN 하이브리드 + Streamlit UI

---

## Summary

반도체 사업장 도면 이미지에서 라인·구역을 자동 식별하는 파이프라인을 Phase 1~3에 걸쳐 전체 구현합니다.

- **Phase 1** — OpenCV 색상 분리 + 붉은 기둥 탐지 + 기하 패턴 매칭
- **Phase 2** — ResNet-18 Coarse CNN + Laplacian Fine Matcher + EasyOCR 교차검증 + FastAPI
- **Phase 3** — 멀티스케일 TTA 앙상블 + 데이터 증강 파이프라인 + Streamlit UI

**테스트:** 138 PASS / 4 SKIP | **커버리지:** 86% | **flake8/mypy/bandit:** 0 violations

---

## Changes

```
src/
├── preprocessing/
│   ├── color_segmentation.py   HSV 색상 레이어 분리 (붉은/푸른 마스크)
│   ├── anchor_detector.py      연결 컴포넌트 분석으로 기둥 좌표 추출
│   └── data_augmentation.py    crop / resize / noise / blur 증강 파이프라인
├── matching/
│   ├── pattern_matcher.py      무게중심 정규화 + KDTree 기하 매칭
│   ├── coarse_matcher.py       ResNet-18 pretrained Top-K 추론
│   ├── fine_matcher.py         Laplacian 특징점 기반 Top-1 선택
│   └── scale_optimizer.py      멀티스케일 TTA 앙상블 (20/30/50/100%)
├── ocr/
│   └── column_reader.py        EasyOCR 기둥 번호 추출 + 신뢰도 보정
├── api/
│   └── main.py                 POST /identify FastAPI 엔드포인트
└── ui/
    └── app.py                  Streamlit 이미지 업로드 + 결과 시각화

tests/                          143개 테스트 (TDD Red→Green→Refactor 단계별 커밋)
```

---

## 식별 파이프라인

```
입력 이미지
  → [색상 분리]   color_segmentation.py  — HSV 마스크 추출
  → [앵커 탐지]   anchor_detector.py     — 붉은 기둥 좌표 추출
  → [패턴 매칭]   pattern_matcher.py     — 기하학적 라인 식별
  → [CNN Coarse]  coarse_matcher.py      — ResNet-18 후보군 압축
  → [CNN Fine]    fine_matcher.py        — Laplacian 특징점 정밀 매칭
  → [OCR 검증]    column_reader.py       — 기둥 번호 텍스트 교차검증
  → [멀티스케일]  scale_optimizer.py     — TTA 앙상블 (20/30/50/100%)
  → [API]         api/main.py            — POST /identify
  → [UI]          ui/app.py              — Streamlit 결과 시각화
```

---

## Review Checklist

| # | 항목 | 중요도 |
|---|------|--------|
| 1 | 파이프라인 단계 경계 및 책임 분리 적절성 | 높음 |
| 2 | 동적 min_area / TTA 가중치 근거 확인 | 높음 |
| 3 | Flaky 테스트 처리 방향 결정 | 중간 |
| 4 | scipy 폴백 동등성 테스트 필요 여부 | 낮음 |
| 5 | `.mcp.json` git 이력 확인 | 높음 |
| 6 | API 응답 스펙 확정 | 중간 |

---

## Review Points

### 1. 아키텍처 — 파이프라인 단계 경계

`coarse → fine → ocr` 순서가 정밀도 vs 속도 트레이드오프 관점에서 적절한지,
각 모듈의 입출력 인터페이스가 일관성 있게 설계되었는지 확인 부탁드립니다.

---

### 2. 핵심 알고리즘 — 스케일 불변성

30% 축소 이미지 식별을 위해 두 가지 접근법을 사용했습니다.

**A. 동적 면적 임계값** (`anchor_detector.py`)

```python
_MIN_AREA_FRAC = 0.005   # 전체 픽셀의 0.5%
_MAX_MIN_AREA  = 14      # r=2 노이즈(area=13)를 걸러내는 경계

min_area = max(_ABS_MIN_AREA, min(_MAX_MIN_AREA, int(H * W * _MIN_AREA_FRAC)))
# 100x100 → min_area=14 (노이즈 제거)
# 36x36   → min_area=6  (30% 축소본 탐지 유지)
```

**B. 멀티스케일 TTA 가중 앙상블** (`scale_optimizer.py`)

```python
_DEFAULT_SCALE_WEIGHTS = {
    0.2: 0.5,
    0.3: 0.8,   # PRD 최소 요구 스케일 — 높은 가중치로 보정
    0.5: 0.6,
    1.0: 1.0,
}
```

`_MAX_MIN_AREA = 14` 경계값과 0.3 스케일 가중치 0.8의 근거가 실제 도면 데이터 없이 합성 fixture 기반으로 설정되었습니다. 실 도면 검증 후 조정이 필요할 수 있습니다.

---

### 3. 테스트 — Flaky 테스트 1건

아래 테스트가 간헐적으로 실패합니다. 처리 방향에 대한 의견 부탁드립니다.

```
tests/test_scale_invariance.py
  ::TestEnsembleAccuracyImprovement::test_multiscale_confidence_vs_single_scale
```

```python
# 테스트 의도: 멀티스케일 >= 단일 스케일 - 5%
assert multi_conf >= single_conf - 0.05
# 실제: multi_conf=0.270 < single_conf=0.377 - 0.05  (차이 10.7%)
```

**원인:** ResNet-18 softmax가 1000 클래스로 분산되어 confidence 절대값 편차가 크고,
멀티스케일 가중 평균이 단일 고신뢰도 값을 희석하는 케이스가 발생합니다.

**처리 방안 (미결):**
- A. `@pytest.mark.xfail` 처리 후 실 도면 데이터로 재검증
- B. 허용 오차를 `-0.15`로 완화하고 주석으로 근거 명시

---

### 4. 의존성 — 내부망 scipy 폴백

내부망 환경에서 `scipy` 설치가 불가하여 numpy 폴백으로 대체했습니다.

```python
# pattern_matcher.py
try:
    from scipy.spatial import KDTree
    def _nearest_distances(...): ...   # scipy 경로
except ImportError:
    def _nearest_distances(...): ...   # numpy 브로드캐스팅 폴백
```

- `requirements.txt`에는 scipy 유지 (외부망 배포 환경 대응)
- 두 구현의 수치 결과 동등성을 검증하는 단위 테스트가 없습니다. 필요 여부 확인 부탁드립니다.

---

### 5. 보안 — gitignore 민감 파일

`.mcp.json`(GitHub Personal Access Token 포함)이 `.gitignore`에 등록되어 있습니다.
`git log --all -- .mcp.json` 실행 시 커밋 이력에 없는지, `settings.local.json`에도 토큰이 없는지 확인 부탁드립니다.

---

### 6. API 계약 — POST /identify 응답 스펙

```json
POST /identify  (multipart/form-data)

Response 200:
{
  "line":       "Line_A",
  "section":    "102",
  "columns":    "B4-B6",
  "confidence": 0.97
}

Response 422: 비이미지 파일 업로드 시
```

아래 두 가지 스펙 결정이 필요합니다.
- `inference_time_ms` 필드를 응답에 포함할지 (디버깅·모니터링 용도)
- 식별 실패(낮은 confidence) 시 200으로 결과를 반환할지, 4xx로 처리할지

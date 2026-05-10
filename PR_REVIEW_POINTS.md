# PR Review Points — Map2Line

---

## PR 제목 제안

현재 파일명 `PR_REVIEW_POINTS.md`는 내부 문서용으로 적합하지만,
실제 PR 제목은 변경 범위와 목적이 드러나야 합니다.

**추천 PR 제목:**
```
feat: Map2Line 식별 엔진 전체 구현 (Phase 1~3)
```

또는 변경 범위를 강조하려면:
```
feat: 도면 기반 라인 자동 식별 시스템 구현 — OpenCV + CNN 하이브리드 + Streamlit UI
```

> **근거:** PR은 Phase 1~3 전체를 한 번에 올리는 상황이므로,
> "무엇을 했는가"보다 "어떤 시스템이 만들어졌는가"를 제목으로 표현하는 것이 검토자에게 더 유효합니다.

---

## 리뷰 요청 포인트

### 1. 아키텍처 — 파이프라인 설계 의도 확인

**요청 내용:**
식별 파이프라인이 3단계로 구성된 이유와 각 단계의 책임 경계가 적절한지 검토해 주세요.

```
입력 이미지
  → [색상 분리]    color_segmentation.py  — HSV 마스크 추출
  → [앵커 탐지]    anchor_detector.py     — 붉은 기둥 좌표 추출
  → [패턴 매칭]    pattern_matcher.py     — 기하학적 라인 식별
  → (선택) [CNN]   coarse_matcher.py      — ResNet-18 후보군 압축
           [Fine]  fine_matcher.py        — Laplacian 특징점 정밀 매칭
           [OCR]   column_reader.py       — 기둥 번호 텍스트 교차검증
  → [멀티스케일]   scale_optimizer.py     — TTA 앙상블 (20/30/50/100%)
  → [API]          api/main.py            — POST /identify
  → [UI]           ui/app.py              — Streamlit 결과 시각화
```

**체크포인트:**
- `coarse → fine → ocr` 순서가 맞는가? (정밀도 vs 속도 트레이드오프)
- 각 모듈의 입출력 인터페이스가 일관성 있게 설계되었는가?

---

### 2. 핵심 알고리즘 — 스케일 불변성 설계 검토

**요청 내용:**
30% 축소 이미지까지 식별 성공을 보장하기 위해 사용한 두 가지 접근법의 적절성을 검토해 주세요.

**접근법 A — 동적 면적 임계값 (anchor_detector.py)**
```python
# 이미지 크기에 비례한 min_area — 고정값 대신 동적 계산
_MIN_AREA_FRAC = 0.005   # 전체 픽셀의 0.5%
_MAX_MIN_AREA  = 14      # r=2 노이즈(area=13)를 걸러내는 경계

min_area = max(_ABS_MIN_AREA, min(_MAX_MIN_AREA, int(H * W * _MIN_AREA_FRAC)))
# 100x100 이미지 → min_area=14 (노이즈 제거)
# 36x36 이미지   → min_area=6  (30% 축소본 탐지 유지)
```

**접근법 B — 멀티스케일 TTA 앙상블 (scale_optimizer.py)**
```python
_DEFAULT_SCALE_WEIGHTS = {
    0.2: 0.5,   # 극소 스케일 — 낮은 가중치
    0.3: 0.8,   # PRD 최소 요구 스케일 — 높은 가중치로 보정
    0.5: 0.6,
    1.0: 1.0,   # 원본 — 최대 가중치
}
```

**체크포인트:**
- `_MAX_MIN_AREA = 14` 경계값의 근거가 충분한가? (실제 도면에서의 앵커 최소 크기 확인 필요)
- TTA 가중치가 0.3 스케일을 1.0 대비 0.8로 설정한 근거가 적절한가?
- 실제 도면 데이터로 검증 전까지 합성 fixture 기반 테스트의 한계가 있음

---

### 3. 테스트 — 알려진 Flaky 테스트 1건

**요청 내용:**
아래 테스트가 간헐적으로 실패합니다. 수정 방향에 대한 의견을 주세요.

**실패 테스트:**
```
tests/test_scale_invariance.py::TestEnsembleAccuracyImprovement
  ::test_multiscale_confidence_vs_single_scale  ← 간헐적 FAIL
```

**실패 원인:**
```python
# 테스트 의도: 멀티스케일 confidence >= 단일 스케일 - 5%
assert multi_conf >= single_conf - 0.05
# 실제 결과: multi_conf=0.270 < single_conf=0.377 - 0.05 (차이 10.7%)
```

**원인 분석:**
- fixture 이미지가 랜덤 노이즈(`np.random.default_rng(42)`)를 포함하는 합성 이미지
- ResNet-18 softmax 출력이 1000 클래스로 분산되어 confidence 절대값이 낮고 편차가 큼
- 멀티스케일 가중 평균이 오히려 단일 고신뢰도 스케일의 값을 희석하는 케이스 발생

**검토 요청 사항:**
- `@pytest.mark.xfail` 처리 후 실 도면 데이터로 재검증하는 방향이 맞는가?
- 또는 허용 오차를 `-0.15`로 완화하고 이유를 주석으로 명시하는 방향이 맞는가?

---

### 4. 의존성 — 내부망 환경 대응

**요청 내용:**
`scipy` 설치 불가 환경에서 numpy 폴백으로 대체한 구조가 프로젝트 정책에 맞는지 확인해 주세요.

```python
# pattern_matcher.py
try:
    from scipy.spatial import KDTree
    def _nearest_distances(...): ...   # scipy 경로
except ImportError:
    def _nearest_distances(...): ...   # numpy 브로드캐스팅 폴백
```

**체크포인트:**
- `requirements.txt`에는 scipy를 유지 (외부망 배포 환경 대응)
- 내부망 환경에서 pytest는 numpy 폴백으로 전부 통과
- 두 구현의 수치 결과가 동일한지 단위 테스트가 없음 → 필요 여부 검토 요청

---

### 5. 보안 및 설정 — gitignore 민감 파일

**요청 내용:**
`.mcp.json`(GitHub 토큰 포함)이 `.gitignore`에 올바르게 등록되어 있는지 확인해 주세요.

```
# .gitignore 등록 항목
.mcp.json          ← GitHub Personal Access Token 포함
.venv/
models/
data/raw/
data/augmented/
```

**체크포인트:**
- `git log --all -- .mcp.json` 실행 시 커밋 이력에 없는지 확인
- `settings.local.json`도 토큰 정보가 없는지 확인

---

### 6. API 계약 — POST /identify 응답 스펙

**요청 내용:**
FastAPI 엔드포인트의 응답 스펙이 Streamlit UI 및 향후 클라이언트와의 계약으로 충분한지 검토해 주세요.

```json
POST /identify
Content-Type: multipart/form-data

Response 200:
{
  "line":       "Line_A",
  "section":    "102",
  "columns":    "B4-B6",
  "confidence": 0.97
}

Response 422: 잘못된 파일 형식 (비이미지 업로드 시)
```

**체크포인트:**
- `inference_time_ms` 필드를 응답에 포함시킬 것인가? (디버깅·모니터링 용도)
- 식별 실패 시(confidence 낮음) 200 vs 4xx 중 어느 쪽이 적합한가?

---

## 리뷰어 체크리스트

| # | 항목 | 중요도 | 담당 |
|---|------|--------|------|
| 1 | 파이프라인 단계 경계 및 책임 분리 적절성 | 높음 | 아키텍처 |
| 2 | 동적 min_area / TTA 가중치 근거 확인 | 높음 | 알고리즘 |
| 3 | Flaky 테스트 처리 방향 결정 | 중간 | 테스트 |
| 4 | scipy 폴백 동등성 테스트 필요 여부 | 낮음 | 의존성 |
| 5 | `.mcp.json` git 이력 확인 | 높음 | 보안 |
| 6 | API 응답 스펙 확정 | 중간 | 인터페이스 |

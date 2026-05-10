# Map2Line — 도면 기반 라인 자동 식별 시스템

[![GitHub](https://img.shields.io/badge/GitHub-ltw070%2FMap2Line-blue?logo=github)](https://github.com/ltw070/Map2Line)

반도체 공장 내 건물 레이아웃(푸른 선)과 기둥 좌표(붉은 표식)를 분석하여,
사용자가 입력한 지도 이미지(캡처·부분 조각·축소/확대본)가 **어떤 라인의 어느 구역인지 실시간으로 판별**하는 지능형 매칭 시스템입니다.

**레포지토리:** https://github.com/ltw070/Map2Line

---

## 핵심 목표

| 목표 | 설명 |
|------|------|
| 높은 식별력 | 붉은색 앵커(기둥) 패턴으로 99% 이상 식별 정확도 |
| 스케일 불변성 | 축소·확대·부분 캡처에서도 강건한 매칭 유지 |
| 자동화 가이드 | 현장 작업자의 도면 탐색 시간 단축 |

---

## 주요 기능

### 하이브리드 식별 엔진
- **Coarse Matching** — CNN으로 후보 라인군을 1차 압축
- **Fine Matching** — 붉은 기둥 배치 기하학으로 라인명·좌표 확정
- **Scale-Invariant 분석** — 크기 변화에 무관한 Keypoint 추출·대조

### 이미지 전처리
- **Color Segmentation** — 푸른 선(구조)·붉은 선/글자(표식) 레이어 분리
- **앵커 포인트 탐지** — 저해상도에서도 붉은 Blob 위치 기반 별자리 매칭
- **OCR 검증** — 해상도 확보 시 기둥 번호 텍스트 교차 검증

### 결과 출력
```
Line A - Section 102 (Column B4-B6)  [신뢰도: 97.3%]
```

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python 3.9+ |
| 이미지 처리 | OpenCV |
| 딥러닝 | PyTorch / TensorFlow, SuperPoint / LoFTR |
| OCR | EasyOCR 또는 PaddleOCR |
| 백엔드 | FastAPI |
| 프론트엔드 | Streamlit 또는 React |

---

## 디렉토리 구조

```
02_Map2Line/
├── .claude/
│   ├── agents/                     # Claude Code SubAgent 정의
│   │   ├── doc-consistency-verifier.md  # SubAgent1: 문서 정합성
│   │   ├── ai-action.md                 # SubAgent2: AI 구현
│   │   ├── test-verifier.md             # SubAgent3: 테스트 검증
│   │   └── compliance-verifier.md       # SubAgent4: 컴플라이언스
│   └── settings.local.json
├── .mcp.json                       # GitHub MCP 서버 설정 (gitignored)
├── .gitignore
├── PRD.md                          # 제품 요구사항 정의서
├── README.md
├── CLAUDE.md                       # Claude Code 작업 가이드
├── REPORT.md                       # 개발 진척 및 이력
└── .venv/                          # Python 가상환경
```

---

## 빠른 시작

```bash
# 가상환경 활성화 (Windows)
.venv\Scripts\activate

# 의존성 설치 (추후 requirements.txt 추가 예정)
pip install -r requirements.txt

# 백엔드 실행
uvicorn src.api.main:app --reload

# 프론트엔드 실행 (Streamlit)
streamlit run src/ui/app.py
```

---

## 성공 지표

| 지표 | 목표값 |
|------|--------|
| 오분류율 | 1% 미만 |
| 응답 속도 | 1.5초 이내 |
| 최소 스케일 | 원본 대비 30% 축소 이미지에서도 식별 성공 |

---

## 로드맵

| Phase | 상태 | 내용 |
|-------|------|------|
| Phase 1 | ✅ 완료 | Task 1-1 환경설정 ✅ · 1-2 색상분리 ✅ · 1-3 앵커탐지 ✅ · 1-4 패턴매칭 ✅ |
| Phase 2 | 진행 중 | Task 2-1 Coarse Matcher ✅ · 2-2 Fine Matcher ✅ · 2-3 OCR ✅ · 2-4 API ⬜ |
| Phase 3 | ⬜ 예정 | 스케일 대응 테스트 + 모바일 캡처 환경 최적화 |

---

> 상세 요구사항 → [PRD.md](./PRD.md) | 구현 계획 → [PLAN.md](./PLAN.md) | 사용 설명서 → [MANUAL.md](./MANUAL.md) | 개발 이력 → [REPORT.md](./REPORT.md)

# CLAUDE.md — Map2Line 작업 가이드

이 문서는 Claude Code가 Map2Line 프로젝트에서 작업할 때 따라야 할 컨텍스트와 규칙을 정의합니다.

---

## 프로젝트 컨텍스트

- **목적:** 반도체 공장 도면 이미지에서 라인·구역을 자동 식별
- **핵심 식별자:** 붉은색 기둥(앵커 포인트)의 기하학적 배치 패턴
- **PRD 위치:** `PRD.md` — 모든 기능 결정의 근거는 이 문서를 기준으로 한다
- **개발 이력:** `REPORT.md` — 진척 사항과 주요 결정은 여기에 기록한다

---

## MCP 서버

### GitHub MCP 설정
- **설정 파일:** `.mcp.json` (gitignored — 토큰 포함)
- **실행 파일:** `D:\cla\99_github-mcp-server\github-mcp-server.exe`
- **용도:** GitHub 이슈·PR 조회, 코드 검색, 리포지토리 관리, 파일 업로드

> `.mcp.json`은 민감 정보(토큰)가 포함되므로 절대 git에 커밋하지 않는다.

### GitHub 접근 규칙 — 작업 규모별 방식 선택

#### MCP 사용 (토큰 효율적)
- **작은 파일 변경**: < 5KB 파일 생성/수정
- **단일 파일 변경**: 한 번에 1-2개 파일
- **API 작업**: 리포지토리 관리, PR 생성, 이슈 관리
- 도구:
  - `mcp__github-general__create_repository`: 리포지토리 생성
  - `mcp__github-general__create_or_update_file`: 파일 생성/수정 (< 5KB)
  - `mcp__github-general__create_pull_request`: PR 생성
  - `mcp__github-general__push_files`: 소수 파일 업로드
  - `mcp__github-general__list_issues`, `mcp__github-general__search_issues`: 이슈 조회

#### Bash + Git 사용 (토큰 절약)
- **큰 파일 변경**: > 10KB 파일 수정
- **대량 파일 변경**: 3개 이상 파일 동시 변경
- **로컬 완성 후 일괄 푸시**: 복잡한 변경사항
- 방식:
  ```bash
  git add <변경된 파일들>
  git commit -m "<type>(<scope>): <요약>"
  git push origin branch
  ```

### 토큰 절약 이유
- MCP: 전체 파일 내용 전송 (100KB = ~25,000 토큰)
- Bash: diff만 전송 (100KB 변경 = ~500 토큰) ← **50배 절약**

---

## SubAgent 구성 (TDD Harness)

모든 구현 작업은 아래 4개 SubAgent를 순서에 따라 호출하는 **TDD + SubAgent 사이클**로 진행한다.

```
SubAgent1 → SubAgent2 → SubAgent3 ┐ (병렬)
                                   ├→ 결과 취합
                        SubAgent4 ┘
```

### SubAgent1 — `@doc-consistency-verifier`
- **역할:** 문서 정합성 검증
- **도구:** Read, Glob, Grep, `mcp__github__list_issues`, `mcp__github__search_issues`, `mcp__github__search_code`
- **시점:** 구현 시작 전, PRD ↔ 코드 불일치 탐지
- **GitHub MCP:** 열린 이슈 조회 → 현재 Task와 연관된 이슈 참고
- **출력:** PASS/FAIL 항목 목록 + 관련 GitHub 이슈 + SubAgent2 우선순위 권고

### SubAgent2 — `@ai-action`
- **역할:** AI 구현 (TDD Red → Green → Refactor)
- **도구:** Read, Write, Edit, Bash, Glob, Grep, `mcp__github__list_issues`, `mcp__github__add_issue_comment`, `mcp__github__issue_write`
- **시점:** SubAgent1 검증 완료 후
- **원칙:** 테스트를 먼저 작성하고 최소 구현으로 통과시킨다
- **GitHub MCP:** Red/Green/Refactor 각 단계 커밋 + 완료 시 이슈 코멘트
- **문서 의무:** Refactor 완료 후 4개 문서(REPORT/README/CLAUDE/MANUAL) 갱신

### SubAgent3 — `@test-verifier` *(SubAgent4와 병렬)*
- **역할:** 테스트 실행 및 커버리지 검증
- **도구:** Read, Bash, Glob, Grep, `mcp__github__issue_write`, `mcp__github__add_issue_comment`, `mcp__github__list_issues`
- **시점:** SubAgent2 구현 완료 후
- **검증:** pytest 실행, PRD 성공 지표(정확도·속도·스케일) 대조
- **GitHub MCP:** FAIL 시 이슈 자동 생성, PASS 시 기존 이슈에 PASS 코멘트

### SubAgent4 — `@compliance-verifier` *(SubAgent3과 병렬)*
- **역할:** 코드 품질·보안·컨벤션 검증
- **도구:** Read, Bash, Glob, Grep, `mcp__github__issue_write`, `mcp__github__add_issue_comment`, `mcp__github__list_issues`
- **시점:** SubAgent2 구현 완료 후
- **검증:** flake8, mypy, bandit, PRD 기술 스택 일치 여부
- **GitHub MCP:** 위반 항목 발생 시 이슈 생성 (HIGH 즉시, MEDIUM·LOW는 3건 이상 시)

---

## TDD 사이클 실행 방법

기능 단위로 아래 순서를 따른다:

```
1. @doc-consistency-verifier 호출
   → FAIL 항목 확인

2. @ai-action 호출 (FAIL 항목 기반 구현)
   → 테스트 작성 → 구현 → 리팩터링

3. @test-verifier + @compliance-verifier 병렬 호출
   → 둘 다 PASS면 완료
   → FAIL 존재 시 → @ai-action 재호출 (피드백 반영)
```

---

## 코드 컨벤션

- **언어:** Python 3.9+
- **린팅:** flake8 (max-line-length=100)
- **타입:** mypy (ignore-missing-imports, python_version=3.10 — mypy 2.0은 3.9 미지원)
- **테스트:** pytest (`tests/` 디렉토리)
- **가상환경:** `.venv/` (Windows: `.venv\Scripts\activate`)

### 금지 사항
- `.mcp.json` git 커밋 금지
- 하드코딩된 토큰·패스워드 금지
- PRD에 없는 기능 선제 구현 금지 (YAGNI)

---

## 주요 파일 위치

| 파일 | 용도 |
|------|------|
| `PRD.md` | 요구사항 정의서 (기능·지표·로드맵) |
| `PLAN.md` | 단계별 구현 계획 (Task·TDD 체크리스트) |
| `REPORT.md` | 개발 진척 및 이력 기록 |
| `MANUAL.md` | 사용자·개발자 사용 설명서 |
| `.claude/agents/` | SubAgent 정의 파일 |
| `.mcp.json` | GitHub MCP 설정 (gitignored) |
| `.gitignore` | `.mcp.json` 포함 |

---

## Task 완료 시 필수 문서 업데이트 (의무)

**모든 Task가 완료될 때마다 아래 4개 문서를 반드시 갱신한다.**  
SubAgent3/4 검증이 PASS된 직후, 커밋 전에 수행한다.

| 문서 | 업데이트 내용 |
|------|-------------|
| `REPORT.md` | 진행 이력 섹션에 작업 기록 추가 |
| `README.md` | 로드맵 상태 테이블, 주요 기능 설명 갱신 |
| `CLAUDE.md` | 새 컨벤션·규칙·금지사항 발생 시 반영 |
| `MANUAL.md` | 사용자 관점 변경사항 (API·UI·설치법 등) 반영 |

> 4개 문서 중 변경이 없는 항목은 "변경 없음" 확인 후 skip 가능.  
> 단, REPORT.md는 예외 없이 항상 업데이트한다.

---

## GitHub 커밋 규칙

Task 완료 + 문서 업데이트 후 반드시 GitHub에 커밋·push한다.

### 커밋 타이밍

아래 시점에 커밋한다:

1. **TDD Red 완료** — 실패하는 테스트 작성 직후
2. **TDD Green 완료** — 테스트 통과 직후 (최소 구현)
3. **TDD Refactor 완료** — 리팩터링 + SubAgent3/4 PASS 직후
4. **문서 업데이트 완료** — 4개 문서 갱신 직후 (위 3번과 묶어도 됨)

### 커밋 메시지 컨벤션

```
<type>(<scope>): <요약>

type:
  feat     — 새 기능
  test     — 테스트 추가·수정
  refactor — 동작 변경 없는 코드 개선
  docs     — 문서 변경
  fix      — 버그 수정
  chore    — 빌드·설정 변경

scope: phase1, phase2, phase3, docs 등

예시:
  test(phase1): color_segmentation Red 테스트 작성
  feat(phase1): color_segmentation Green 구현
  refactor(phase1): HSV 범위 상수 분리
  docs: Task 1-2 완료 후 4개 문서 갱신
```

### 커밋 절차

```bash
git add <변경된 파일들>
git commit -m "<type>(<scope>): <요약>"
git push
```

> `git add .` 대신 파일을 명시적으로 지정한다 (민감 파일 방지).  
> `.mcp.json`은 절대 스테이징하지 않는다.

---

## REPORT.md 업데이트 규칙

작업 완료 시 `REPORT.md`의 **진행 이력** 섹션에 다음 형식으로 추가한다:

```markdown
### YYYY-MM-DD — [작업 제목]
- **변경 내용:** 무엇을 했는가
- **근거:** 왜 했는가 (PRD 섹션 참조)
- **결과:** SubAgent3/4 검증 결과 요약
- **다음 작업:** 후속 필요 사항
```

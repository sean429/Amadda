# Amadda Overall Architecture

이 문서는 현재 Amadda의 핵심 구조를 한 번에 보기 위한 설명서다.

## 목적

Amadda는 사용자의 작업 맥락을 저장하고, 나중에 빠르게 다시 진입할 수 있도록 돕는 로컬 중심 컨텍스트 복구 도구다.

현재 구현 범위는 아래 네 축으로 나뉜다.

- 로컬 Windows 컨텍스트 수집
- Chrome extension 기반 브라우저 탭 컨텍스트 수집 (15분 자동 + 수동)
- LLM 기반 작업 요약 (Gemini API)
- 음성 명령 입력 (로컬 Whisper)

## 주요 구성 요소

### 1. Desktop UI

- [window.py](C:\graduation\Amadda\app\ui\window.py)

역할:

- 텍스트 명령 입력
- 음성 명령 입력 (Voice 버튼 → Whisper 변환 → 자동 실행)
- 실행 결과 및 로그 출력
- 확인이 필요한 액션에 대한 사용자 승인
- Tracked Apps 다이얼로그 (앱 아이콘 포함)

### 2. Intent Parser

- [parser.py](C:\graduation\Amadda\app\intents\parser.py)

역할:

- 사용자의 입력을 규칙 기반 intent로 변환
- 예: `save snapshot`, `restore latest snapshot`, `open ...`

### 3. Permission Layer

- [service.py](C:\graduation\Amadda\app\permissions\service.py)

역할:

- 위험한 액션에 대해 확인 요구
- 현재는 `sleep`, `shutdown` 등에 사용

### 4. Dispatcher

- [service.py](C:\graduation\Amadda\app\dispatcher\service.py)

역할:

- 파싱된 intent를 적절한 action service로 연결

### 5. Action Layer

#### Snapshot actions

- [snapshots.py](C:\graduation\Amadda\app\actions\snapshots.py)
- [snapshot_collectors.py](C:\graduation\Amadda\app\actions\snapshot_collectors.py)

역할:

- Windows 프로세스/창 스냅샷 수집
- SQLite 저장

#### Browser actions

- [browser.py](C:\graduation\Amadda\app\actions\browser.py)

역할:

- URL 열기
- 기존 snapshot에 URL이 있으면 다시 열기

#### System actions

- [system.py](C:\graduation\Amadda\app\actions\system.py)

역할:

- sleep, shutdown 같은 시스템 액션 처리

#### LLM actions

- [llm.py](C:\graduation\Amadda\app\actions\llm.py)

역할:

- 최근 3개 스냅샷의 window/browser_tab 항목을 통합
- Gemini API(`gemini-2.5-flash-lite`)로 작업 요약 생성
- `GEMINI_API_KEY` 환경변수 필요 (Google AI Studio 무료 발급)

#### Voice actions

- [voice.py](C:\graduation\Amadda\app\actions\voice.py)

역할:

- sounddevice로 5초 마이크 녹음
- 로컬 Whisper(`small` 모델)로 한국어 음성 → 텍스트 변환
- 완전 오프라인, API 비용 없음

### 6. FastAPI Local Backend

- [server.py](C:\graduation\Amadda\app\api\server.py)

역할:

- 데스크톱 앱과 함께 로컬 API 실행
- `POST /command`
- `GET /snapshots/latest`
- `POST /browser/snapshot`

### 7. SQLite Storage

- [sqlite.py](C:\graduation\Amadda\app\db\sqlite.py)
- [models.py](C:\graduation\Amadda\app\models.py)

역할:

- snapshot과 snapshot item 저장
- 프로세스, 창, 브라우저 탭을 같은 구조로 저장

## 현재 데이터 흐름

### A. Windows snapshot flow

```text
User command -> Parser -> Dispatcher -> SnapshotActionService
-> WindowsSnapshotCollector -> SnapshotRepository -> SQLite
```

### B. Browser snapshot flow

```text
[15분 알람 또는 아이콘 클릭]
Chrome service worker -> chrome.windows.getLastFocused -> POST /browser/snapshot
-> FastAPI -> SnapshotRepository -> SQLite
```

### C. GUI unified snapshot flow

```text
User: save snapshot
-> SnapshotActionService
-> WindowsSnapshotCollector (process/window 수집, 서브프로세스 그룹화)
-> get_latest_browser_tab_items (DB에서 최근 browser_tab 병합)
-> chrome.exe 항목 제거 (browser_tab으로 대체)
-> SnapshotRepository -> SQLite
```

### D. LLM 요약 flow

```text
User: 요약해줘 (텍스트 또는 음성)
-> Parser -> Dispatcher
-> get_recent_snapshots(n=3) (최근 3개 스냅샷 통합)
-> _format_snapshots_for_prompt (window + browser_tab 중복 제거)
-> Gemini API -> 작업 요약 텍스트 -> GUI 로그 출력
```

## Snapshot 저장 구조

모든 컨텍스트는 같은 저장 구조를 사용한다.

### snapshots

- 스냅샷 단위

### snapshot_items

- 개별 항목 단위
- 현재 item 종류:
  - `process`
  - `window`
  - `browser_tab`

## 현재 설계 의도

이 구조는 과도하게 복잡하지 않으면서도 나중에 확장하기 쉽게 유지하는 것이 목적이다.

예를 들어 앞으로 아래를 추가할 수 있다.

- YouTube timestamp
- VS Code workspace path
- 문서 앱 최근 파일 경로
- 다중 브라우저 지원

핵심은 새 컨텍스트 소스를 넣더라도 기존 dispatcher/UI/SQLite 구조를 크게 바꾸지 않는 것이다.

## 현재 한계

- restore는 URL 재오픈 수준에 머무름 (앱 재실행, 창 배치 복원 미구현)
- 브라우저는 현재 Chrome만 지원
- 앱별 고급 컨텍스트 미구현 (VS Code workspace path, Word 문서 경로 등)
- 프로세스 필터는 휴리스틱 기반이라 환경별 조정이 필요할 수 있음

## 관련 문서

- [browser_snapshot_flow.md](C:\graduation\Amadda\docs\browser_snapshot_flow.md)
- [windows_snapshot_flow.md](C:\graduation\Amadda\docs\windows_snapshot_flow.md)

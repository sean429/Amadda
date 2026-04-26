# Amadda Tracked Apps / Snapshot Follow-up

기준 커밋: 최신 작업 반영

## 지금까지 반영된 것

### 1. Tracked Apps UI 추가

- 메인 GUI에 `Tracked Apps` 버튼 추가
- PySide6 다이얼로그에서 현재 실행 중 프로세스를 확인 가능
- 같은 프로세스 이름은 그룹으로 묶어서 표시
- 표시 정보:
  - 프로세스 이름
  - PID 목록
  - 보이는 윈도우 제목 목록
  - 실행 파일 경로 목록
- 선택한 tracked app 목록은 SQLite에 저장

### 2. tracked app 저장 구조 추가

- 기존 DB `data/amadda.db` 안에 `tracked_processes` 테이블 추가
- 현재는 `process_name` 중심으로 저장
- 목적:
  - `chrome.exe`처럼 동일 이름 프로세스를 앱 단위로 추적
  - UI 재진입 시 선택 상태를 안정적으로 복원

### 3. snapshot 필터링 추가

- Windows snapshot 수집 시 tracked app만 포함되도록 변경
- 즉, tracked app으로 선택하지 않은 프로세스/윈도우는 스냅샷에서 제외

### 4. snapshot 보존 개수 제한 추가

- 새 snapshot 저장 시 오래된 snapshot을 자동 정리하도록 변경
- 현재 기본값:
  - `SNAPSHOT_RETENTION_MAX = 288`
- 기준:
  - 최신 snapshot 288개만 유지
- 정리 시점:
  - 앱 시작 시 아님
  - 새 snapshot 저장 직후

### 5. Browser 자동 수집 구현

- Chrome extension에 15분 주기 자동 전송 추가
- `chrome.alarms` API 사용 (MV3 service worker는 언제든 종료될 수 있어 `setInterval` 불가)
- 변경 파일:
  - `browser_extension/manifest.json` — `"alarms"` 권한 추가
  - `browser_extension/service_worker.js` — 알람 등록 및 자동 전송 로직 추가
- 동작 방식:
  - 확장 설치(`onInstalled`) 및 service worker 재시작(`onStartup`) 시 알람 자동 등록
  - 15분마다 `sendSnapshot()` 자동 호출
  - 백엔드가 꺼져 있으면 조용히 실패 (콘솔 경고만)
  - 수동 클릭 기능과 배지 피드백은 그대로 유지
- 버그 수정:
  - `currentWindow: true` → `chrome.windows.getLastFocused({ windowTypes: ["normal"] })`로 변경
  - DevTools/알람 컨텍스트에서 탭이 0개로 반환되는 문제 해결

### 6. 서브 프로세스 중복 제거

- 변경 파일: `app/actions/snapshot_collectors.py`
- 기존 문제: `chrome.exe`, `Code.exe` 등은 서브 프로세스를 수십 개 띄워 동일 앱이 스냅샷에 수십 개 중복 저장됨
- 수정 방식: `(process_name, executable_path)` 기준으로 그룹화
  - 앱당 process 아이템 1개
  - 고유한 창 제목마다 window 아이템 1개
- 효과: 노이즈 항목 대폭 감소, 스냅샷 가독성 향상

### 7. GUI snapshot + browser 상태 통합

- 변경 파일: `app/actions/snapshots.py`, `app/db/sqlite.py`
- 기존 문제: GUI `save snapshot`은 Windows 프로세스/창 정보만 저장, URL 없음
- 수정 방식:
  - `SnapshotRepository.get_latest_browser_tab_items()` 추가
  - `save_snapshot()` 실행 시 DB의 최근 browser_tab 항목을 자동으로 병합
  - browser_tab이 있을 경우 chrome.exe process/window 항목은 제외 (중복 방지)
- 효과: 단일 스냅샷에 Windows 앱 컨텍스트 + 브라우저 URL이 함께 저장됨

### 8. Tracked Apps 아이콘 표시

- 변경 파일: `app/ui/window.py`
- `QFileIconProvider`를 사용해 각 앱의 실행 파일에서 시스템 아이콘 추출
- Process Name 열에 앱 아이콘 표시
- 별도 의존성 없이 Qt 내장 기능만 사용

### 9. LLM 기반 작업 요약 (Gemini API)

- 추가 파일: `app/actions/llm.py`
- 변경 파일: `app/intents/parser.py`, `app/dispatcher/service.py`, `app/config.py`, `requirements.txt`
- 의존성: `google-genai` 패키지
- 모델: `gemini-2.5-flash-lite` (무료 티어)
- API 키: 환경변수 `GEMINI_API_KEY`로 주입 (Google AI Studio에서 무료 발급)
- 동작 방식:
  - 최근 3개 스냅샷의 window/browser_tab 항목을 중복 제거 후 통합
  - Gemini에 컨텍스트 전달, 구체적인 파일명/탭 제목 언급하도록 프롬프트 설계
  - 결과를 GUI 로그에 출력
- 트리거 명령: `요약해줘`, `summarize`, `뭐하고 있었어` 등

### 10. 음성 입력 (로컬 Whisper)

- 추가 파일: `app/actions/voice.py`
- 변경 파일: `app/ui/window.py`, `requirements.txt`
- 의존성: `openai-whisper`, `sounddevice`
- 모델: `whisper small` (첫 실행 시 자동 다운로드 ~140MB, 이후 캐시)
- 동작 방식:
  - GUI에 `Voice` 버튼 추가
  - 클릭 시 5초간 마이크 녹음 (QThread로 UI 블로킹 없음)
  - 녹음 완료 후 Whisper로 한국어 변환 (`language="ko"`, `fp16=False`)
  - 변환된 텍스트를 입력창에 자동 입력 후 즉시 실행
- 완전 오프라인 동작, API 비용 없음

## 현재 한계 / 아직 안 된 것

### 1. 앱별 복구 컨텍스트 미구현

- VS Code workspace path, Word 문서 경로 등 앱 내부 상태는 아직 수집 안 됨
- 현재는 창 제목 수준에서 멈춤

### 2. restore가 URL 재오픈 중심

- `restore latest snapshot` 명령은 브라우저 URL만 다시 열음
- Windows 앱 재실행, 창 배치 복원 등은 미구현

### 3. 스냅샷 단위와 아이템 단위 분리

- 보존 정책은 snapshot 개수 기준
- 실제 DB 증가량은 snapshot_items 수에 더 크게 영향받을 수 있음

## 다음 작업 후보

### 앱별 복구 컨텍스트 확장

- VS Code: workspace path, 현재 열린 파일 경로
- Word: 문서 파일 경로
- 목표: 단순 창 제목이 아니라 실제 복구 가능한 컨텍스트 저장

## 커밋 정리 시 유의사항

- `__pycache__` 변경분은 커밋에서 제외
- `data/amadda.db`는 로컬 상태 파일이므로 커밋에서 제외
- 기능 코드 위주 대상:
  - `app/`
  - `browser_extension/`
  - `docs/`

# Amadda Tracked Apps / Snapshot Follow-up

기준 커밋: `0e2a687` `docs update`

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

## 현재 한계 / 아직 안 된 것

### 1. GUI `save snapshot`에는 URL이 포함되지 않음

- 현재 GUI 저장은 Windows 프로세스/윈도우 snapshot만 저장
- 브라우저 URL은 Chrome extension이 별도로 `/browser/snapshot`으로 전송할 때만 저장됨

### 2. 기존 데이터 즉시 정리 미구현

- 보존 개수 제한은 "앞으로 저장되는 흐름"에 적용됨
- 이미 쌓인 데이터를 즉시 줄이는 별도 정리 액션은 아직 없음

### 4. snapshot 단위와 snapshot item 단위가 분리되어 있음

- 현재 보존 정책은 `snapshot` 개수를 기준으로 동작
- 실제 DB 증가량은 `snapshot_items` 수에 더 크게 영향받을 수 있음

## 다음 작업 제안

### 우선순위 1. GUI snapshot과 browser 상태 연결

- GUI `save snapshot` 시 최근 browser 상태를 함께 저장하도록 구조 정리
- 후보 방식:
  - 최근 browser 상태 캐시를 합쳐서 저장
  - 또는 GUI가 browser 상태 동기화를 요청한 뒤 저장

### 우선순위 3. 기존 데이터 정리 액션 추가

- 일회성 DB 정리 명령 또는 버튼 추가
- 예:
  - 최신 N개만 남기고 즉시 삭제
  - browser snapshot만 따로 정리

### 우선순위 4. 앱별 복구 컨텍스트 확장

- `Explorer`는 제외
- 후보 앱:
  - VS Code
  - Word
- 목표:
  - 단순 프로세스 이름이 아니라 실제 복구 가능한 컨텍스트 저장
- 예:
  - VS Code: workspace path, file path
  - Word: document path

## 커밋 정리 시 유의사항

- `__pycache__` 변경분은 커밋에서 제외하는 것이 좋음
- `data/amadda.db`는 로컬 상태 파일이므로 커밋에서 제외하는 것이 좋음
- 기능 코드 위주 대상:
  - `app/`
  - `browser_extension/`
  - `docs/`

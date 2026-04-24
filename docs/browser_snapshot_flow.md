# Amadda Browser Snapshot Flow

이 문서는 Amadda MVP의 Chrome extension 기반 브라우저 스냅샷 기능이 어떻게 동작하는지 설명한다.

## 목적

Windows 프로세스/창 제목 수집만으로는 실제 브라우저 작업 맥락 복구가 부족하다.  
그래서 Chrome extension이 현재 창의 탭 정보를 직접 수집해서 로컬 FastAPI로 보내고, Amadda가 이를 SQLite에 저장한다.

## 관련 파일

### Chrome extension

- [manifest.json](C:\graduation\Amadda\browser_extension\manifest.json)
- [service_worker.js](C:\graduation\Amadda\browser_extension\service_worker.js)
- [README.md](C:\graduation\Amadda\browser_extension\README.md)

### FastAPI backend

- [server.py](C:\graduation\Amadda\app\api\server.py)
- [sqlite.py](C:\graduation\Amadda\app\db\sqlite.py)
- [models.py](C:\graduation\Amadda\app\models.py)

## 전체 흐름

```text
[User clicks Chrome extension icon]
          |
          v
[Chrome service worker]
  - gets current window tabs
  - extracts url/title/active
          |
          v
POST http://127.0.0.1:8765/browser/snapshot
          |
          v
[FastAPI endpoint]
  - validates request
  - converts tabs to SnapshotItem
  - stores them as one snapshot
          |
          v
[SQLite]
  - snapshots
  - snapshot_items
```

## Extension 동작 원리

Chrome extension은 Manifest V3 기반이다.

- `manifest.json`
  - MV3 선언
  - `tabs` 권한 사용
  - `http://127.0.0.1:8765/*` 로컬 백엔드 접근 허용
  - background service worker 등록
- `service_worker.js`
  - 확장 아이콘 클릭 이벤트 수신
  - `chrome.tabs.query({ currentWindow: true })` 호출
  - 현재 Chrome 창에 열려 있는 탭을 읽음
  - 각 탭에서 아래 3개만 추출
    - `url`
    - `title`
    - `active`
  - JSON으로 FastAPI에 POST

이 확장은 popup UI 없이 아이콘 클릭만으로 동작한다.  
성공하면 배지에 `OK`, 실패하면 `ERR`를 잠깐 표시한다.

## FastAPI 동작 원리

`POST /browser/snapshot` 엔드포인트가 확장 요청을 받는다.

요청 예시는 아래와 같다.

```json
{
  "browser": "chrome",
  "tabs": [
    {
      "url": "https://example.com",
      "title": "Example",
      "active": true
    }
  ]
}
```

서버는 이 요청을 받은 뒤:

1. Pydantic 모델로 요청 검증
2. 각 탭을 `SnapshotItem`으로 변환
3. `item_type="browser_tab"` 지정
4. 기존 `SnapshotRepository.save_snapshot(...)` 호출
5. SQLite `snapshots`, `snapshot_items` 테이블에 저장

즉 브라우저 데이터도 별도 테이블을 만들지 않고 기존 snapshot 구조를 그대로 재사용한다.

## SQLite 저장 방식

각 브라우저 탭은 `snapshot_items`의 한 행으로 저장된다.

주요 매핑은 아래와 같다.

- `app_name`: `Chrome`
- `title`: 탭 제목, active 탭이면 뒤에 `[active]` 표시
- `url`: 실제 탭 URL
- `item_type`: `browser_tab`
- `process_name`: `chrome`
- `executable_path`: `None`

이 방식의 장점은 기존 snapshot 조회 API와 저장 로직을 그대로 사용할 수 있다는 점이다.

## 왜 Chrome extension이 필요한가

Windows 프로세스 수집만으로는 정확한 탭 URL을 얻기 어렵다.

- OS 레벨에서는 보통 프로세스 이름, 창 제목 정도만 안정적으로 수집 가능
- 실제 탭 URL은 브라우저 내부 정보라서 extension이 가장 정확함
- 이후 YouTube timestamp 같은 기능도 extension 기반이 자연스럽다

즉, 브라우저 컨텍스트 복구 품질을 올리려면 extension 방식이 맞다.

## 현재 범위

- 현재 Chrome 창의 탭만 수집
- `url`, `title`, `active`만 전송
- **15분 주기 자동 전송** (`chrome.alarms` 기반)
- 아이콘 클릭으로 수동 즉시 전송 가능 (배지 피드백 포함)
- YouTube timestamp 미구현
- 불필요한 popup/options UI 미구현

## 자동 전송 구현 방식

MV3 service worker는 언제든 브라우저에 의해 종료될 수 있어 `setInterval`이 동작하지 않는다.
대신 `chrome.alarms` API를 사용한다.

```text
[Extension 설치 또는 Chrome 재시작]
  → onInstalled / onStartup 리스너
  → ensureAlarm() : 알람이 없으면 15분 주기 알람 생성

[15분 경과]
  → alarms.onAlarm 리스너 발동
  → sendSnapshot() 호출
  → 백엔드 꺼져 있으면 조용히 실패 (console.warn)
```

수동 클릭은 기존과 동일하게 동작하며, 성공/실패 배지를 3초간 표시한다.

## 설치 방법

### 1. Amadda 앱 실행

```powershell
.venv\Scripts\python -m app.main
```

### 2. Chrome extension 로드

1. `chrome://extensions` 이동
2. `Developer mode` 켜기
3. `Load unpacked` 클릭
4. `C:\graduation\Amadda\browser_extension` 선택

### 3. 스냅샷 전송

1. Chrome 현재 창에서 원하는 탭들을 열어둠
2. 확장 아이콘 클릭
3. 로컬 FastAPI에 브라우저 탭 스냅샷 전송

## 확인 방법

### FastAPI 최신 snapshot 확인

```powershell
Invoke-WebRequest http://127.0.0.1:8765/snapshots/latest | Select-Object -ExpandProperty Content
```

응답에서 아래가 보이면 정상이다.

- `item_type: "browser_tab"`
- 각 탭의 `url`
- 각 탭의 `title`

## 이후 확장 방향

다음 단계에서는 아래를 붙일 수 있다.

- YouTube timestamp 수집
- 현재 창이 아니라 전체 브라우저 창 수집
- 주기적 자동 스냅샷
- 브라우저별 분리 지원
- Windows 프로세스 snapshot과 브라우저 snapshot을 하나의 통합 snapshot으로 합치기

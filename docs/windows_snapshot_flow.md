# Amadda Windows Snapshot Flow

이 문서는 Amadda의 Windows 로컬 컨텍스트 수집기가 어떻게 동작하는지 설명한다.

## 목적

사용자가 작업을 중단하기 직전의 로컬 실행 상태를 저장하기 위해 Windows에서 실행 중인 프로세스와 보이는 창 제목을 수집한다.

현재 수집 대상:

- 실행 중인 프로세스 이름
- 보이는 창 제목
- 가능한 경우 실행 파일 경로

## 관련 파일

- [snapshot_collectors.py](C:\graduation\Amadda\app\actions\snapshot_collectors.py)
- [snapshots.py](C:\graduation\Amadda\app\actions\snapshots.py)
- [sqlite.py](C:\graduation\Amadda\app\db\sqlite.py)
- [models.py](C:\graduation\Amadda\app\models.py)

## 전체 흐름

```text
[User enters: save snapshot]
          |
          v
[Intent parser]
          |
          v
[Dispatcher]
          |
          v
[SnapshotActionService]
          |
          v
[WindowsSnapshotCollector]
  - enumerate visible windows
  - enumerate processes
  - apply filters
  - build SnapshotItem list
          |
          v
[SnapshotRepository]
  - save snapshot row
  - save snapshot_items rows
          |
          v
[SQLite]
```

## 수집기 동작 원리

Windows 수집기는 [snapshot_collectors.py](C:\graduation\Amadda\app\actions\snapshot_collectors.py) 에 있다.

수집 순서는 아래와 같다.

1. Win32 API로 보이는 창 제목 수집
2. `psutil`로 프로세스 목록 수집
3. 프로세스 이름, PID, 실행 경로 확인
4. 창 제목과 PID를 매핑
5. 시스템/백그라운드 프로세스 필터 적용
6. `SnapshotItem` 리스트 생성

### 생성되는 item 타입

- `process`
- `window`

## 필터링 원리

모든 프로세스를 그대로 저장하면 restore 후보가 너무 많아지고 노이즈가 심해진다.  
그래서 현재는 아래 기준으로 필터링한다.

- 시스템 핵심 프로세스 ignore
- `service.exe`, `tray.exe`, `launcher.exe`, `container.exe` 패턴 ignore
- 특정 키워드가 포함된 백그라운드 프로세스 ignore
- 특정 시스템/드라이버/보안 관련 경로 ignore
- 창 제목이 있는 프로세스는 우선 유지
- `chrome.exe`, `Code.exe`, `explorer.exe`, `python.exe` 같은 작업용 앱은 유지

## SQLite 저장 방식

Windows 수집 데이터도 기존 snapshot 구조를 사용한다.

### snapshots

- snapshot 단위 메타데이터 저장

### snapshot_items

각 프로세스 또는 창 항목이 한 행으로 저장된다.

주요 컬럼:

- `app_name`
- `title`
- `url`
- `item_type`
- `process_name`
- `executable_path`
- `created_at`

## 로그

`save snapshot` 실행 시 UI에서 아래 같은 로그를 볼 수 있다.

- `Enumerated ... visible window title(s).`
- `Ignored ... process(es) by filter.`
- `Collected ... processes after filtering.`
- `Collected executable paths for ... process item(s).`

이 로그는 실제로 무엇이 얼마나 수집되었는지 검증하기 위한 것이다.

## 제한 사항

- 일부 프로세스는 실행 파일 경로 접근이 막혀 있을 수 있다
- 일부 창은 제목이 없거나 PID 매핑이 불완전할 수 있다
- 필터는 공통 휴리스틱이라서 PC마다 완벽하지 않다
- 실제 앱 복구 품질을 높이려면 브라우저 URL, VS Code workspace 같은 앱별 데이터가 더 필요하다

## 현재 역할

Windows snapshot은 현재 Amadda에서 브라우저 외 로컬 컨텍스트를 담당한다.

- 프로세스 수준의 작업 힌트 제공
- 창 제목 기반 컨텍스트 보강
- 복구 후보 앱 식별 보조

정확한 브라우저 복구는 별도의 Chrome extension 수집이 담당한다.

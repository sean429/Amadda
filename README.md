# Amadda

> "아 맞다" — AI가 당신의 작업 흐름을 기억합니다  
> A local-first AI assistant that remembers your work context so you don't have to

Amadda는 사용자의 작업 맥락(실행 중인 앱, 창 제목, 브라우저 탭)을 자동으로 수집·저장하고,  
작업 재개 시 그 흐름을 빠르게 복원해주는 Windows 데스크톱 AI 비서입니다.

---

## 주요 기능

- **자동 스냅샷** — 15분마다 현재 앱·창·브라우저 탭을 자동 저장
- **작업 요약** — "뭐 하고 있었어?"라고 물으면 Gemini가 한국어로 요약
- **작업 복구** — 이전 스냅샷의 브라우저 탭·VS Code 워크스페이스를 한 번에 복원
- **음성 명령** — 로컬 Whisper 기반 오프라인 음성 인식
- **웨이크워드** — "아맞다" 또는 "아맞다야"로 마이크 자동 활성화
- **앱/사이트 실행** — "유튜브 켜줘", "vscode 열어줘" 등 자연어 명령
- **웹 검색** — "파이썬 검색해줘", "네이버에서 날씨 찾아줘" 등

---

## 설치 방법

### 1. 다운로드

[Releases](../../releases) 페이지에서 `Amadda_v0.1.2.zip`을 다운로드하고 원하는 폴더에 압축 해제합니다.

```
Amadda.exe          ← 메인 실행 파일
_internal/          ← 런타임 의존성 (건드리지 않아도 됩니다)
browser_extension/  ← Chrome 확장 프로그램
```

### 2. Chrome 확장 설치

브라우저 탭 자동 수집을 위해 Chrome 확장을 설치해야 합니다.

1. Chrome 주소창에 `chrome://extensions` 입력
2. 우측 상단 **개발자 모드** 활성화
3. **압축 해제된 확장 프로그램을 로드합니다** 클릭
4. 압축 해제한 폴더 안의 `browser_extension/` 폴더 선택

### 3. Amadda 실행

`Amadda.exe`를 더블클릭하여 실행합니다.

### 4. Gemini API 키 설정

작업 요약 기능을 사용하려면 Gemini API 키가 필요합니다.

1. [Google AI Studio](https://aistudio.google.com/app/apikey)에서 무료 API 키 발급
2. Amadda 우측 상단 메뉴(☰) → **Settings** → API 키 입력 후 저장

> API 키는 `%APPDATA%\Amadda\settings.json`에 로컬 저장되며 외부로 전송되지 않습니다.

---

## 사용법

### 음성 명령

마이크 버튼을 누르거나 **"아맞다"** 라고 말하면 음성 입력이 활성화됩니다.

### 텍스트 명령

입력창에 직접 타이핑해도 됩니다.

### 주요 명령어

| 명령 예시 | 동작 |
|---|---|
| `저장해줘` | 현재 스냅샷 저장 |
| `뭐 하고 있었어` | 최근 작업 AI 요약 |
| `어제 하던 거 다시 열어줘` | 최신 스냅샷 복구 |
| `유튜브 켜줘` | YouTube 열기 |
| `파이썬 검색해줘` | Google에서 검색 |
| `vscode 켜줘` | VS Code 실행 |
| `넌 누구야` | Amadda 자기소개 |
| `컴퓨터 꺼줘` | 종료 (확인 필요) |

전체 명령어 목록은 [docs/commands.md](docs/commands.md)를 참고하세요.

---

## 기술 스택

| 구성 요소 | 기술 |
|---|---|
| 데스크톱 UI | pywebview 5.x + HTML/CSS/JS |
| 로컬 API | FastAPI + uvicorn |
| 데이터 저장 | SQLite3 |
| 프로세스 수집 | psutil + Win32 ctypes |
| 음성 인식 | openai-whisper (tiny, 로컬) |
| 음성 활동 감지 | silero-vad 5.x |
| 마이크 입력 | sounddevice |
| LLM 요약 | Google Gemini 2.5 Flash Lite |
| 브라우저 확장 | Chrome Manifest V3 |

---

## 한계

- Chrome만 지원 (Firefox, Edge 미지원)
- Word 문서는 전체 경로 복구 불가 (창 제목 기반 수집)
- 앱 내부 상태(스크롤 위치, 커서 등)는 복원하지 않음
- Windows 전용

---

## 라이선스

졸업 프로젝트 용도로 제작되었습니다. 학술 및 연구 목적으로만 사용 가능합니다.

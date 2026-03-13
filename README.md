# amadda

> 기억을 이끄는 지능형 워크스페이스 맥락 복구 비서  
> Intelligent workspace context recovery assistant

amadda는 사용자가 작업을 중단할 당시의 **핵심 작업 맥락**을 저장하고  
다시 돌아왔을 때 빠르게 작업 흐름에 복귀할 수 있도록 돕는 시스템입니다.

이 프로젝트는 완전한 상태 복원이 아니라  
**맥락 복구(Context Recovery)** 에 초점을 맞춥니다.

예를 들어 다음과 같은 정보를 저장하고 복구합니다.

- 실행 중이던 주요 앱 정보
- 브라우저 탭 URL
- YouTube 영상 재생 시점
- 직전 작업 흐름에 대한 요약 정보

---

## 1. Why amadda?

컴퓨터를 껐다 켜거나 잠시 자리를 비운 뒤 다시 작업을 시작할 때  
사용자는 단순히 프로그램만 다시 여는 것이 아니라  
**어디까지 무엇을 하고 있었는지**를 다시 떠올려야 합니다.

기존 복구 기능은 주로 앱 실행 수준에 머무르지만  
실제 사용자가 필요로 하는 것은 다음과 같은 **작업 맥락**입니다.

- 어떤 창을 띄워 두었는지
- 어떤 웹페이지를 보고 있었는지
- 어떤 영상의 몇 분 지점을 보고 있었는지
- 어떤 프로젝트 흐름으로 작업 중이었는지

amadda는 이러한 문제를 해결하기 위해  
작업 환경 자체보다 **작업 재진입에 필요한 맥락 정보**를 수집하고 복구합니다.

---

## 2. Core Idea

> Forget the "What", Just do the "Work"

amadda의 핵심 아이디어는  
사용자가 다시 세팅하는 데 시간을 쓰지 않고  
곧바로 원래의 작업 흐름으로 돌아갈 수 있도록 돕는 것입니다.

이 프로젝트는 다음 질문에서 출발했습니다.

- "어제 뭐 하고 있었지?"
- "어떤 탭 열어놨었지?"
- "유튜브 어디까지 봤더라?"
- "다시 세팅하려면 또 몇 분 걸리지?"

amadda는 이 질문에 대해  
사용자의 **'아 맞다'** 를 대신 떠올려주는 비서를 목표로 합니다.

---

## 3. Key Features

### 3-1. Smart Snapshot
사용자가 작업을 중단하는 시점의 주요 맥락 정보를 저장합니다.

수집 예시:
- 실행 중인 애플리케이션 이름
- 창 제목
- 실행 경로 또는 파일 경로
- Chrome 탭 URL
- YouTube 재생 시간

---

### 3-2. Context Recap
저장된 기록을 바탕으로  
직전 작업 흐름을 한 줄 요약으로 제공합니다.

예시:
- 캡스톤 발표 자료 수정 중
- FastAPI 서버 구조 정리 중
- 강의 영상 32분 지점까지 시청함

---

### 3-3. Workspace Re-entry
저장된 스냅샷을 기반으로  
필요한 앱과 웹페이지를 다시 열어  
빠르게 작업에 재진입할 수 있도록 지원합니다.

---

### 3-4. Voice Command
음성 명령을 통해 저장 및 복구 기능을 자연스럽게 사용할 수 있도록 확장합니다.

예시:
- "아마다 저장해줘"
- "어제 하던 거 다시 열어줘"

---

## 4. What makes it different?

amadda는 단순한 앱 재실행 도구가 아닙니다.

### 기존 방식
- 프로그램만 다시 열림
- 구체적인 작업 위치는 복원하지 못함
- 사용자가 직접 기억을 더듬어야 함

### amadda
- 작업 흐름 중심의 맥락 저장
- 브라우저와 데스크톱 환경을 함께 고려
- 재생 시점, 탭 정보 등 실제 작업 단서를 제공
- LLM 기반 작업 요약으로 재진입 부담 감소

---

## 5. Tech Stack

### Desktop / Client
- Python 3.x
- PySide6 or PyQt6

### Backend
- FastAPI
- SQLite

### Browser
- Chrome Extension
- JavaScript
- Manifest V3

### AI / Voice
- Gemini API
- OpenAI Whisper

### System / Window Control
- psutil
- pygetwindow
- pywinauto

---

## 6. System Architecture

```text
[Desktop Client]
  ├─ collects running app/window info
  ├─ requests snapshot save / recovery
  └─ provides tray UI and recovery actions

[Chrome Extension]
  ├─ collects current tab URLs
  └─ tracks YouTube timestamp

[Local Database]
  └─ stores snapshot data and context records

[FastAPI Server]
  ├─ processes collected context data
  ├─ connects to LLM modules
  └─ handles recap / command logic

[LLM Module]
  ├─ summarizes work context
  └─ interprets voice/user commands
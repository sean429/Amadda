# Amadda

> 음성으로 명령하고, 권한으로 실행하는 데스크톱 AI 비서  
> A permission-based desktop AI assistant for voice-driven task execution and context recovery

Amadda는 사용자로부터 허용된 권한 범위 내에서  
음성 명령을 이해하고, 데스크톱 환경을 인식하며,  
실제 시스템 동작을 수행하는 윈도우 기반 AI 비서입니다.

이 프로젝트는 단순한 질의응답형 AI가 아니라  
사용자의 작업 흐름을 보조하는 실행형 인터페이스를 목표로 합니다.

대표 기능으로는 다음이 포함됩니다.

- 음성 기반 절전 / 종료 / 실행 명령
- 작업 맥락 스냅샷 저장
- 직전 작업 흐름 요약
- 주요 앱 및 브라우저 환경 복귀 지원

---

## 1. Why Amadda?

컴퓨터를 껐다 켜거나 잠시 자리를 비운 뒤 다시 작업을 시작할 때  
사용자는 단순히 프로그램만 다시 여는 것이 아니라  
**어디까지 무엇을 하고 있었는지**를 다시 떠올려야 합니다.

기존 복구 기능은 주로 앱 실행 수준에 머무르지만  
실제 사용자가 필요로 하는 것은 다음과 같은 **작업 맥락**입니다.

- 어떤 창을 띄워 두었는지
- 어떤 웹페이지를 보고 있었는지
- 어떤 영상의 몇 분 지점을 보고 있었는지
- 어떤 프로젝트 흐름으로 작업 중이었는지

Amadda는 이러한 문제를 해결하기 위해  
작업 환경 자체보다 **작업 재진입에 필요한 맥락 정보**를 수집하고 복구합니다.

---

## 2. Core Idea

> Forget the "What", Just do the "Work"

Amadda의 핵심 아이디어는  
사용자가 다시 세팅하는 데 시간을 쓰지 않고  
곧바로 원래의 작업 흐름으로 돌아갈 수 있도록 돕는 것입니다.

이 프로젝트는 다음 질문에서 출발했습니다.

- "어제 뭐 하고 있었지?"
- "어떤 탭 열어놨었지?"
- "유튜브 어디까지 봤더라?"
- "다시 세팅하려면 또 몇 분 걸리지?"

Amadda는 이 질문에 대해  
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

Amadda는 단순한 앱 재실행 도구가 아닙니다.

### 기존 방식

- 프로그램만 다시 열림
- 구체적인 작업 위치는 복원하지 못함
- 사용자가 직접 기억을 더듬어야 함

### Amadda

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
  ```

---

## 7. Project Scope

Amadda는 **완전 복원**이 아니라  
**맥락 복구(Context Recovery)** 를 목표로 합니다.

즉 모든 프로그램의 내부 상태를 완벽하게 되돌리는 것이 아니라  
사용자가 빠르게 다시 작업 흐름에 들어갈 수 있도록  
핵심 단서를 복원하는 데 집중합니다.

### Supported context examples

- 주요 앱 실행 정보
- 브라우저 탭 목록
- YouTube 시청 시점
- 작업 요약 정보

### Not the main goal

- 모든 앱의 내부 편집 상태 완전 복원
- OS 전체 상태 스냅샷
- 가상 머신 수준의 세션 복제

---

## 8. Expected Benefits

- 작업 재개 시간 단축
- 반복적인 환경 재구성 부담 감소
- 작업 흐름 유지
- 사용자 생산성 향상
- 음성 기반 접근성 확장

---

## 9. Development Roadmap

- [x] 프로젝트 주제 및 방향성 정의
- [x] 핵심 기능 설계
- [ ] FastAPI 서버 구축
- [ ] SQLite 스키마 설계
- [ ] Chrome Extension 프로토타입 구현
- [ ] YouTube timestamp 수집 기능 구현
- [ ] 데스크톱 클라이언트 UI 구현
- [ ] 스냅샷 저장 및 복구 엔진 구현
- [ ] LLM 기반 작업 요약 기능 추가
- [ ] 음성 명령 처리 기능 통합
- [ ] 통합 테스트 및 데모 구성

---

## 10. Demo Scenario

1. 사용자가 여러 개의 앱과 브라우저 탭을 열어 작업한다.
2. Amadda가 현재 작업 맥락을 스냅샷으로 저장한다.
3. 사용자는 작업을 종료하거나 자리를 비운다.
4. 이후 Amadda가 저장된 정보를 바탕으로 작업 흐름을 요약해 보여준다.
5. 사용자는 복구 기능을 통해 주요 작업 환경에 빠르게 다시 진입한다.

---

## 11. Future Work

- VS Code 작업 파일 복귀 지원
- 더 정교한 창 위치 복구
- 작업 유형별 분류 기능
- 사용자 패턴 기반 자동 저장 추천
- 더 자연스러운 음성 인터페이스
- 다중 브라우저 지원

---

## 12. Limitations

앱마다 외부 제어 가능 범위가 다르기 때문에  
모든 프로그램의 상태를 동일한 수준으로 복원할 수는 없습니다.

따라서 Amadda는  
완전 복원이 아닌 **실용적인 맥락 복구**를 지향합니다.

---

## 13. Team / Project Info

- Project: Amadda
- Type: Graduation Project
- Goal: Restore meaningful work context for faster task resumption

---

## 14. License

This project is for academic and research purposes.  
License details will be added later.

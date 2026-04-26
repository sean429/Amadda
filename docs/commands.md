# Amadda 명령어 레퍼런스

음성 또는 텍스트로 입력할 수 있는 명령어 목록입니다.

---

## 스냅샷

| 예시 입력 | 동작 |
|---|---|
| `저장해줘` / `스냅샷 저장` / `save snapshot` | 현재 열린 창과 브라우저 탭을 스냅샷으로 저장 |
| `어제 하던 거 다시 열어줘` / `restore snapshot` | 마지막 스냅샷의 브라우저 탭을 모두 다시 열기 |

---

## AI 요약

| 예시 입력 | 동작 |
|---|---|
| `뭐 하고 있었어` / `요약해줘` / `summarize` | 최근 스냅샷 3개를 기반으로 작업 내용을 Gemini가 한국어로 요약 |

---

## 검색

| 예시 입력 | 동작 |
|---|---|
| `파이썬 검색해줘` | Google에서 "파이썬" 검색 |
| `유튜브에서 로파이 검색해줘` | YouTube에서 "로파이" 검색 |
| `네이버에서 날씨 찾아줘` | Naver에서 "날씨" 검색 |
| `구글에서 AI 검색해` | Google에서 "AI" 검색 |

> 사이트 지정 없으면 Google이 기본값입니다.

---

## 사이트 열기

| 예시 입력 | 열리는 URL |
|---|---|
| `유튜브 켜줘` / `youtube 열어줘` | https://www.youtube.com |
| `구글 켜줘` / `google 열어줘` | https://www.google.com |
| `네이버 켜줘` | https://www.naver.com |
| `카카오 켜줘` | https://www.kakao.com |
| `깃허브 켜줘` / `github 열어줘` | https://github.com |
| `지메일 켜줘` / `gmail 열어줘` | https://mail.google.com |

> 직접 URL 지정: `https://example.com 열어줘`

---

## 앱 실행

| 예시 입력 | 실행되는 앱 |
|---|---|
| `워드 켜줘` / `word 열어줘` | Microsoft Word |
| `엑셀 켜줘` / `excel 열어줘` | Microsoft Excel |
| `파워포인트 켜줘` / `ppt 켜줘` | Microsoft PowerPoint |
| `메모장 켜줘` / `notepad 열어줘` | 메모장 |
| `커맨드 창 켜줘` / `cmd 켜줘` / `명령 프롬프트 켜줘` | 명령 프롬프트 |
| `파워쉘 켜줘` / `powershell 열어줘` | PowerShell |
| `탐색기 켜줘` / `파일 탐색기 켜줘` / `explorer 켜줘` | Windows 탐색기 |
| `vscode 켜줘` / `브이에스코드 켜줘` | Visual Studio Code |

---

## 시스템

| 예시 입력 | 동작 | 확인 필요 |
|---|---|---|
| `절전해줘` / `sleep` | 컴퓨터 절전 모드 | O |
| `컴퓨터 꺼줘` / `shutdown` | 컴퓨터 종료 | O |

---

## 참고

- 음성 입력 시 마이크 버튼을 누르면 5초간 녹음 후 자동 인식됩니다.
- 키워드가 포함되어 있으면 인식됩니다. 예: "유튜브 좀 켜줄 수 있어?" → 유튜브 열기
- 확인이 필요한 명령(절전, 종료)은 UI에서 한 번 더 승인해야 실행됩니다.

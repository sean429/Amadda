from __future__ import annotations

from app.config import GEMINI_API_KEY
from app.models import ActionResult, SnapshotRecord


def _format_snapshots_for_prompt(snapshots: list[SnapshotRecord]) -> str:
    windows: list[str] = []
    tabs: list[str] = []

    for snapshot in snapshots:
        for item in snapshot.items:
            if item.item_type == "window":
                if item.title and item.title not in windows:
                    windows.append(item.title)
            elif item.item_type == "browser_tab":
                entry = f"{item.title} ({item.url})" if item.url else (item.title or item.url or "")
                if entry and entry not in tabs:
                    tabs.append(entry)

    lines: list[str] = []
    if windows:
        lines.append("열린 창 제목:")
        for w in windows:
            lines.append(f"  - {w}")
    if tabs:
        lines.append("브라우저 탭:")
        for t in tabs:
            lines.append(f"  - {t}")

    return "\n".join(lines)


class LLMActionService:
    def summarize_recent_snapshots(self, snapshots: list[SnapshotRecord]) -> ActionResult:
        if not GEMINI_API_KEY:
            return ActionResult(
                success=False,
                message="GEMINI_API_KEY 환경변수가 설정되지 않았습니다. 터미널에서 set GEMINI_API_KEY=your_key 후 앱을 재시작해주세요.",
            )

        try:
            from google import genai
        except ImportError:
            return ActionResult(
                success=False,
                message="google-genai 패키지가 설치되지 않았습니다. pip install google-genai 후 재시작해주세요.",
            )

        context = _format_snapshots_for_prompt(snapshots)
        if not context.strip():
            return ActionResult(success=False, message="요약할 스냅샷 내용이 없습니다.")


        prompt = f"""아래는 사용자가 컴퓨터에서 마지막으로 작업하던 상태입니다.
아래 항목들을 빠짐없이 참고하여, 사용자가 무엇을 하고 있었는지 한국어로 구체적으로 설명해주세요.

규칙:
- 창 제목, 탭 제목에 나온 파일명·강의명·영상 제목 등을 그대로 언급하세요.
- 브라우저 탭이 여러 개면 각각 무엇을 보고 있었는지 모두 설명하세요.
- VS Code 창이 있으면 어떤 파일을 편집 중이었는지 언급하세요.
- 문장 수 제한 없이 항목별로 충분히 설명하세요.

{context}"""

        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
            )
            summary = response.text.strip()
            return ActionResult(success=True, message=summary)
        except Exception as exc:
            return ActionResult(success=False, message=f"Gemini API 호출 실패: {exc}")

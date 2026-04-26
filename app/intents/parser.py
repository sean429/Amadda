from __future__ import annotations

import re
from urllib.parse import quote_plus

from app.models import Intent


URL_PATTERN = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)


class RuleBasedIntentParser:
    def parse(self, text: str) -> Intent:
        normalized = text.strip()
        lowered = normalized.lower()

        if not normalized:
            return Intent(intent="unknown", raw_text=text)

        if self._is_restore_snapshot(lowered, normalized):
            return Intent(intent="restore_latest_snapshot", raw_text=text)

        if self._is_save_snapshot(lowered, normalized):
            return Intent(intent="save_snapshot", raw_text=text)

        if self._is_shutdown(lowered, normalized):
            return Intent(intent="shutdown", requires_confirmation=True, raw_text=text)

        if self._is_sleep(lowered, normalized):
            return Intent(intent="sleep", requires_confirmation=True, raw_text=text)

        url_match = URL_PATTERN.search(normalized)
        if self._is_open_url(lowered, normalized) and url_match:
            url = url_match.group(0)
            if url.startswith("www."):
                url = f"https://{url}"
            return Intent(intent="open_url", params={"url": url}, raw_text=text)

        if self._is_summarize(lowered, normalized):
            return Intent(intent="summarize", raw_text=text)

        open_url_intent = self._try_open_named_url(normalized)
        if open_url_intent is not None:
            return open_url_intent

        open_app_intent = self._try_open_app(normalized)
        if open_app_intent is not None:
            return open_app_intent

        search_intent = self._try_search(normalized)
        if search_intent is not None:
            return search_intent

        return Intent(intent="unknown", raw_text=text)

    def _is_summarize(self, lowered: str, normalized: str) -> bool:
        return (
            "summarize" in lowered
            or "summary" in lowered
            or "요약" in normalized
            or "뭐 하고 있었" in normalized
            or "뭐하고 있었" in normalized
            or "어제 뭐 했" in normalized
        )

    def _is_restore_snapshot(self, lowered: str, normalized: str) -> bool:
        return (
            ("restore" in lowered and "snapshot" in lowered)
            or "어제 하던 거 다시 열어줘" in normalized
            or "다시 열어줘" in normalized and "어제" in normalized
        )

    def _is_save_snapshot(self, lowered: str, normalized: str) -> bool:
        return (
            ("save" in lowered and "snapshot" in lowered)
            or normalized == "저장해줘"
            or ("저장" in normalized and "스냅샷" in normalized)
        )

    def _is_shutdown(self, lowered: str, normalized: str) -> bool:
        return (
            "shutdown" in lowered
            or "turn off" in lowered
            or "power off" in lowered
            or normalized == "컴퓨터 꺼줘"
            or ("컴퓨터" in normalized and "꺼" in normalized)
        )

    def _is_sleep(self, lowered: str, normalized: str) -> bool:
        return "sleep" in lowered or normalized == "절전해줘" or "절전" in normalized

    def _is_open_url(self, lowered: str, normalized: str) -> bool:
        return "open" in lowered or "링크 열어줘" in normalized or "열어줘" in normalized

    # Named site shortcuts → open_url
    _NAMED_URLS: list[tuple[tuple[str, ...], str]] = [
        (("유튜브", "youtube"), "https://www.youtube.com"),
        (("구글", "google"), "https://www.google.com"),
        (("네이버", "naver"), "https://www.naver.com"),
        (("카카오", "kakao"), "https://www.kakao.com"),
        (("깃허브", "github"), "https://github.com"),
        (("지메일", "gmail"), "https://mail.google.com"),
    ]

    def _try_open_named_url(self, normalized: str) -> Intent | None:
        lowered = normalized.lower()
        for keywords, url in self._NAMED_URLS:
            if any(kw in lowered for kw in keywords):
                if "켜" in normalized or "열어" in normalized or "open" in lowered:
                    return Intent(intent="open_url", params={"url": url}, raw_text=normalized)
        return None

    # App launch shortcuts → open_app
    _APP_KEYWORDS: list[tuple[tuple[str, ...], str]] = [
        (("워드", "word"), "word"),
        (("엑셀", "excel"), "excel"),
        (("파워포인트", "powerpoint", "ppt"), "powerpoint"),
        (("메모장", "notepad"), "notepad"),
        (("커맨드", "cmd", "명령 프롬프트", "명령프롬프트"), "cmd"),
        (("파워쉘", "파워셸", "powershell"), "powershell"),
        (("탐색기", "파일 탐색기", "explorer"), "explorer"),
        (("브이에스코드", "vscode", "vs code"), "vscode"),
    ]

    def _try_open_app(self, normalized: str) -> Intent | None:
        lowered = normalized.lower()
        for keywords, app in self._APP_KEYWORDS:
            if any(kw in lowered for kw in keywords):
                if "켜" in normalized or "열어" in normalized or "실행" in normalized or "open" in lowered:
                    return Intent(intent="open_app", params={"app": app}, raw_text=normalized)
        return None

    _SEARCH_TRIGGER = re.compile(r"검색해줘|검색해|검색|찾아줘|찾아봐|search")

    _SEARCH_SITES: list[tuple[tuple[str, ...], str, str]] = [
        (("유튜브", "youtube"),  "youtube", "https://www.youtube.com/results?search_query={q}"),
        (("네이버", "naver"),    "naver",   "https://search.naver.com/search.naver?query={q}"),
        (("구글", "google"),     "google",  "https://www.google.com/search?q={q}"),
    ]

    _STRIP_WORDS = re.compile(
        r"유튜브에서|유튜브|youtube에서|youtube"
        r"|네이버에서|네이버|naver에서|naver"
        r"|구글에서|구글|google에서|google"
        r"|검색해줘|검색해|검색|찾아줘|찾아봐|search"
        r"|에서",
        re.IGNORECASE,
    )

    def _try_search(self, normalized: str) -> Intent | None:
        if not self._SEARCH_TRIGGER.search(normalized):
            return None

        lowered = normalized.lower()
        search_url_template = "https://www.google.com/search?q={q}"
        for keywords, _name, template in self._SEARCH_SITES:
            if any(kw in lowered for kw in keywords):
                search_url_template = template
                break

        query = self._STRIP_WORDS.sub("", normalized).strip()
        if not query:
            return None

        url = search_url_template.format(q=quote_plus(query))
        return Intent(intent="open_url", params={"url": url}, raw_text=normalized)

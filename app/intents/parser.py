from __future__ import annotations

import re

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

        return Intent(intent="unknown", raw_text=text)

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

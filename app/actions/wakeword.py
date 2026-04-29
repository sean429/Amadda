from __future__ import annotations

import threading

SAMPLE_RATE   = 16000
CHUNK_SAMPLES = 512
SILENCE_MS    = 600
MAX_SECONDS   = 4   # wake word는 짧음

_whisper_tiny = None
_vad_model    = None

_WAKE_PATTERNS = ["아맞다", "아 맞다", "아맞다야", "아 맞다야"]


def _get_tiny_model():
    global _whisper_tiny
    if _whisper_tiny is None:
        import whisper
        _whisper_tiny = whisper.load_model("tiny")
    return _whisper_tiny


def _get_vad():
    global _vad_model
    if _vad_model is None:
        from silero_vad import load_silero_vad
        _vad_model = load_silero_vad()
    return _vad_model


def _matches(text: str) -> bool:
    cleaned = text.strip().replace(" ", "").lower()
    return any(p.replace(" ", "") in cleaned for p in _WAKE_PATTERNS)


class WakeWordListener:
    """
    백그라운드에서 마이크를 상시 모니터링.
    wake word 감지 시 _triggered 플래그를 세우고,
    프론트엔드가 poll_and_clear()로 확인 후 음성 명령 흐름 진입.
    """

    def __init__(self) -> None:
        self._enabled  = False
        self._triggered = threading.Event()
        self._stop      = threading.Event()
        self._thread: threading.Thread | None = None

    # ── 공개 API ──────────────────────────────────────────────────

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._enabled = True
        self._stop.clear()
        self._triggered.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._enabled = False
        self._stop.set()

    @property
    def is_active(self) -> bool:
        return self._enabled

    def poll_and_clear(self) -> bool:
        """프론트엔드 폴링용. 트리거 여부 반환 후 플래그 초기화."""
        triggered = self._triggered.is_set()
        if triggered:
            self._triggered.clear()
        return triggered

    # ── 내부 루프 ─────────────────────────────────────────────────

    def _loop(self) -> None:
        import numpy as np
        import torch
        import sounddevice as sd
        from silero_vad import VADIterator

        while not self._stop.is_set():
            # 트리거 후 프론트엔드가 처리할 때까지 대기 (마이크 충돌 방지)
            if self._triggered.is_set():
                self._stop.wait(0.3)
                continue

            vad = VADIterator(
                _get_vad(),
                threshold=0.5,
                sampling_rate=SAMPLE_RATE,
                min_silence_duration_ms=SILENCE_MS,
                speech_pad_ms=80,
            )

            chunks: list[np.ndarray] = []
            speech_started = False
            max_chunks = int(MAX_SECONDS * SAMPLE_RATE / CHUNK_SAMPLES)

            try:
                with sd.InputStream(
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype="float32",
                    blocksize=CHUNK_SAMPLES,
                ) as stream:
                    for _ in range(max_chunks):
                        if self._stop.is_set() or self._triggered.is_set():
                            break
                        data, _ = stream.read(CHUNK_SAMPLES)
                        chunk = data.flatten()
                        chunks.append(chunk)
                        event = vad(torch.from_numpy(chunk), return_seconds=False)
                        if event:
                            if "start" in event:
                                speech_started = True
                            elif "end" in event and speech_started:
                                break
            except Exception:
                self._stop.wait(1.0)
                continue

            if not speech_started or not chunks or self._stop.is_set():
                continue

            # 스트림 닫힌 후 Whisper tiny로 wake word 확인
            try:
                audio = np.concatenate(chunks)
                result = _get_tiny_model().transcribe(audio, language="ko", fp16=False)
                if _matches(result["text"]):
                    self._triggered.set()
            except Exception:
                pass

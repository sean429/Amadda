from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

SAMPLE_RATE = 16000
RECORD_SECONDS = 5

_whisper_model = None


def _get_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        _whisper_model = whisper.load_model("small")
    return _whisper_model


def record_and_transcribe() -> str:
    import numpy as np
    import sounddevice as sd

    audio: np.ndarray = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    audio = audio.flatten()

    model = _get_model()
    result = model.transcribe(audio, language="ko", fp16=False)
    return result["text"].strip()

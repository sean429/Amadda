from __future__ import annotations

from typing import Callable

SAMPLE_RATE = 16000
CHUNK_SAMPLES = 512        # silero-vad requires exactly 512 samples per chunk at 16kHz (~32ms)
MAX_SECONDS = 10           # absolute recording ceiling
SILENCE_DURATION_MS = 800  # silence after speech → stop
MIN_SPEECH_SAMPLES = int(0.5 * SAMPLE_RATE)  # ignore spurious noise shorter than 0.5s

_whisper_model = None
_vad_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        _whisper_model = whisper.load_model("small")
    return _whisper_model


def _get_vad_model():
    global _vad_model
    if _vad_model is None:
        from silero_vad import load_silero_vad
        _vad_model = load_silero_vad()
    return _vad_model


def record_and_transcribe(on_status: Callable[[str], None] | None = None) -> str:
    import numpy as np
    import sounddevice as sd
    import torch
    from silero_vad import VADIterator

    vad = VADIterator(
        _get_vad_model(),
        threshold=0.5,
        sampling_rate=SAMPLE_RATE,
        min_silence_duration_ms=SILENCE_DURATION_MS,
        speech_pad_ms=100,
    )

    chunks: list[np.ndarray] = []
    speech_started = False
    samples_since_start = 0
    max_chunks = int(MAX_SECONDS * SAMPLE_RATE / CHUNK_SAMPLES)

    if on_status:
        on_status("듣는 중...")

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=CHUNK_SAMPLES,
    ) as stream:
        for _ in range(max_chunks):
            data, _ = stream.read(CHUNK_SAMPLES)
            chunk = data.flatten()
            chunks.append(chunk)

            event = vad(torch.from_numpy(chunk), return_seconds=False)

            if event:
                if "start" in event:
                    speech_started = True
                    samples_since_start = 0
                elif "end" in event and speech_started and samples_since_start >= MIN_SPEECH_SAMPLES:
                    break

            if speech_started:
                samples_since_start += CHUNK_SAMPLES

    if on_status:
        on_status("변환 중...")

    audio = np.concatenate(chunks) if chunks else np.array([], dtype="float32")
    if len(audio) == 0:
        return ""

    result = _get_whisper_model().transcribe(audio, language="ko", fp16=False)
    return result["text"].strip()

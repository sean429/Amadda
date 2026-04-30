# -*- mode: python ; coding: utf-8 -*-
"""
Amadda — PyInstaller build spec
onedir 방식: dist/Amadda/ 폴더 생성
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = Path(SPECPATH)
VENV = ROOT / ".venv" / "Lib" / "site-packages"

# ── 데이터 파일 ──────────────────────────────────────────────────────
datas = []

# 프론트엔드 HTML/CSS/JS
datas += [(str(ROOT / "app" / "ui" / "frontend"), "app/ui/frontend")]

# Whisper 애셋 (mel_filters, vocab, tiktoken 등)
datas += [(str(VENV / "whisper" / "assets"), "whisper/assets")]
datas += [(str(VENV / "whisper" / "normalizers"), "whisper/normalizers")]

# silero-vad 모델 파일
datas += [(str(VENV / "silero_vad" / "data"), "silero_vad/data")]

# pywebview 리소스
datas += collect_data_files("webview")

# tiktoken 인코딩 파일
datas += collect_data_files("tiktoken")
datas += collect_data_files("tiktoken_ext")

# ── 숨겨진 imports ────────────────────────────────────────────────────
hiddenimports = [
    # torch / torchaudio
    "torch",
    "torch.nn",
    "torch.jit",
    "torchaudio",
    # whisper
    "whisper",
    "whisper.tokenizer",
    "whisper.audio",
    "whisper.decoding",
    "whisper.transcribe",
    # silero-vad
    "silero_vad",
    "silero_vad.utils_vad",
    # sounddevice / soundfile
    "sounddevice",
    "soundfile",
    "cffi",
    "_cffi_backend",
    # fastapi / uvicorn
    "fastapi",
    "fastapi.middleware.cors",
    "fastapi.staticfiles",
    "fastapi.responses",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "anyio",
    "anyio._backends._asyncio",
    # pydantic
    "pydantic",
    "pydantic.deprecated.decorator",
    # psutil
    "psutil",
    "psutil._pswindows",
    # google-genai
    "google.genai",
    # webview
    "webview",
    "webview.platforms.winforms",
    # tiktoken
    "tiktoken",
    "tiktoken.core",
    "tiktoken_ext",
    "tiktoken_ext.openai_public",
]

# ── 바이너리 (torch DLL 등) ───────────────────────────────────────────
binaries = []
binaries += collect_dynamic_libs("torch")

# ── 분석 ─────────────────────────────────────────────────────────────
a = Analysis(
    [str(ROOT / "app" / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "PIL",
        "cv2",
        "notebook",
        "IPython",
        "scipy",
        "sklearn",
        "pandas",
        "tensorflow",
        "keras",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Amadda",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX 압축 끔 — torch DLL 손상 방지
    console=False,      # 콘솔 창 숨김
    disable_windowed_traceback=False,
    icon=None,          # 아이콘 있으면 경로 넣기: "assets/icon.ico"
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Amadda",
)

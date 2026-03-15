# Amadda Environment Setup

This file explains how to recreate the local development environment after cloning the repository.

## Prerequisites

- Python 3.11 or newer
- `pip`
- Windows is the main target platform for real `sleep` and `shutdown` behavior

## 1. Clone and move into the project

```bash
git clone <your-repo-url>
cd Amadda
```

## 2. Create a virtual environment

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### Windows CMD

```bat
py -m venv .venv
.venv\Scripts\activate.bat
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Run the app

### Cross-platform

```bash
python -m app.main
```

### Windows convenience script

```bat
run.bat
```

## 5. Smoke test

After launch, verify the following:

- The PySide6 desktop window opens
- The action log appears
- `save snapshot` works
- `restore latest snapshot` works
- `open https://example.com` opens a browser
- `sleep` and `shutdown` show confirmation prompts

## 6. Notes

- `.venv/` is intentionally ignored by git and must be created locally on each machine
- `data/*.db` is also ignored by git, so each machine creates its own local SQLite database
- On non-Windows systems, `sleep` and `shutdown` are safe stubs in this MVP
- The current snapshot collector is still a stub and does not yet capture real Windows app state
- Whisper can later be inserted before the text parser as a speech-to-text layer
- Gemini or another LLM can later be inserted after the rule-based parser as a fallback interpretation layer

## 7. Troubleshooting

### Import errors

If you see missing module errors, confirm the virtual environment is activated and rerun:

```bash
pip install -r requirements.txt
```

### Port already in use

The app now selects a free local API port automatically. If you still see a binding issue, close any previous Amadda process and rerun.

### Qt plugin or display issues on Linux

If running headless for a smoke test:

```bash
QT_QPA_PLATFORM=offscreen python -m app.main
```

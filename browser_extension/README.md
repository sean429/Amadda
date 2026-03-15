# Amadda Chrome Extension

Minimal Manifest V3 extension for sending the current Chrome window tab snapshot to the local Amadda FastAPI backend.

## What it sends

- `url`
- `title`
- `active`

## How to load

1. Open `chrome://extensions`
2. Enable `Developer mode`
3. Click `Load unpacked`
4. Select the `browser_extension/` folder

## How to use

1. Start the Amadda app so the local FastAPI server is running on `http://127.0.0.1:8765`
2. Click the extension icon
3. The extension sends the current window tabs to `POST /browser/snapshot`
4. Check the backend logs or `GET /snapshots/latest`

## Notes

- The extension intentionally has no popup UI yet.
- It only snapshots the current Chrome window.
- YouTube timestamp collection is not included yet.

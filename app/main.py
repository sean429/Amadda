from __future__ import annotations

import sys

from app.ui.window import run_desktop_app


def main() -> int:
    return run_desktop_app()


if __name__ == "__main__":
    sys.exit(main())

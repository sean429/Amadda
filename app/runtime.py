from __future__ import annotations

import socket

from app.config import API_HOST, API_PORT


def select_api_port(preferred_port: int = API_PORT) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((API_HOST, preferred_port))
            return preferred_port
        except OSError:
            sock.bind((API_HOST, 0))
            return int(sock.getsockname()[1])

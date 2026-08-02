"""TCP line transport for Studio ↔ Runner (localhost)."""

from __future__ import annotations

import socket
import threading
from collections.abc import Callable, Iterator
from typing import Any

from screenflow.runner_protocol import decode_line, encode_message


def connect_client(host: str, port: int, *, timeout: float = 30.0) -> socket.socket:
    sock = socket.create_connection((host, port), timeout=timeout)
    sock.settimeout(None)
    return sock


def serve_once(host: str = "127.0.0.1", port: int = 0) -> tuple[socket.socket, int]:
    """
    Bind a listening socket. Returns (listener, bound_port).
    Caller accepts one connection then may close the listener.
    """
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, port))
    listener.listen(1)
    bound = int(listener.getsockname()[1])
    return listener, bound


def send_msg(sock: socket.socket, obj: dict[str, Any]) -> None:
    sock.sendall(encode_message(obj))


def iter_messages(sock: socket.socket) -> Iterator[dict[str, Any]]:
    buf = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf += chunk
        while True:
            nl = buf.find(b"\n")
            if nl < 0:
                break
            line, buf = buf[:nl], buf[nl + 1 :]
            msg = decode_line(line)
            if msg is not None:
                yield msg


def read_thread(
    sock: socket.socket,
    on_message: Callable[[dict[str, Any]], None],
    on_disconnect: Callable[[], None] | None = None,
) -> threading.Thread:
    def _run() -> None:
        try:
            for msg in iter_messages(sock):
                on_message(msg)
        finally:
            if on_disconnect:
                on_disconnect()

    t = threading.Thread(target=_run, name="runner-ipc-read", daemon=True)
    t.start()
    return t

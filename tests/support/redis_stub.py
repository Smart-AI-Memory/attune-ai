"""A real listening socket that answers PING like a Redis would.

Used by tests that must pin WHICH endpoint a probe dials (library-review
H1). It is not a stand-in for the probe or the resolver — only for the
server on the far side of a real connection — so a test can put a real
endpoint at an address that is provably not a hard-coded one, without
needing a ``redis-server`` binary.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import socket
import threading


def read_command(rfile) -> list[bytes] | None:
    """Read one RESP command (array or inline) from a connection."""
    line = rfile.readline()
    if not line:
        return None
    if not line.startswith(b"*"):
        return line.strip().split()
    parts = []
    for _ in range(int(line[1:])):
        header = rfile.readline()
        if not header.startswith(b"$"):
            return None
        payload = rfile.read(int(header[1:]) + 2)
        parts.append(payload[:-2])
    return parts


class RespStub:
    """A listening socket on an ephemeral port that replies to PING."""

    #: RESP3 handshake reply — redis-py >= 5.1 opens with ``HELLO 3``.
    _HELLO_REPLY = (
        b"%3\r\n"
        b"$6\r\nserver\r\n$5\r\nredis\r\n"
        b"$7\r\nversion\r\n$5\r\n7.0.0\r\n"
        b"$5\r\nproto\r\n:3\r\n"
    )

    def __init__(self) -> None:
        self._sock = socket.socket()
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(8)
        self.port: int = self._sock.getsockname()[1]
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn: socket.socket) -> None:
        with conn, conn.makefile("rb") as rfile:
            while True:
                command = read_command(rfile)
                if command is None:
                    return
                verb = command[0].upper() if command else b""
                if verb == b"HELLO":
                    conn.sendall(self._HELLO_REPLY)
                elif verb == b"PING":
                    conn.sendall(b"+PONG\r\n")
                else:
                    conn.sendall(b"+OK\r\n")

    def close(self) -> None:
        self._stop.set()
        self._sock.close()


def closed_port() -> int:
    """A port with nothing listening on it."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

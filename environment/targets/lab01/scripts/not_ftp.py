#!/usr/bin/env python3
"""Small plaintext credential-prompt service used by the Lab 01 exercise."""

import selectors
import socket
import sys


PORTS = (21, 2121)
PROBE_TIMEOUT = 2
LOGIN_TIMEOUT = 30


def looks_like_service_probe(data: bytes) -> bool:
    """Recognize common protocol probes so scanners do not stall on a fake FTP login."""
    payload = data.strip().upper()
    if not payload or len(payload) > 64 or b" " in payload:
        return True
    if any(byte < 32 or byte > 126 for byte in payload):
        return True
    command = payload.split(None, 1)[0]
    return command in {
        b"ACCT", b"AUTH", b"CDUP", b"CWD", b"DATA", b"EHLO", b"FEAT", b"GET",
        b"HEAD", b"HELP", b"HELO", b"LIST", b"MDTM", b"MKD", b"MODE", b"NOOP",
        b"OPTIONS", b"PASS", b"PASV", b"PORT", b"POST", b"PWD", b"QUIT", b"REIN",
        b"REST", b"RETR", b"RTSP/", b"SITE", b"SIZE", b"SMNT", b"STAT", b"STOR",
        b"STOU", b"STRU", b"SYST", b"TYPE", b"USER", b"HTTP/", b"RPC",
    }


def serve_client(client: socket.socket, address: tuple[str, int]) -> None:
    client.settimeout(PROBE_TIMEOUT)
    with client:
        print(f"Received connection from {address}", flush=True)
        try:
            client.sendall(b"Enter your username: ")
            username = client.recv(1024)
            if not username:
                return
            if looks_like_service_probe(username):
                return
            client.sendall(b"Enter your password: ")
            client.settimeout(LOGIN_TIMEOUT)
            client.recv(1024)
            client.sendall(
                "I am not FTP and I just stole your credentials (◣_◢)!\n".encode(
                    "utf-8"
                )
            )
        except (ConnectionError, TimeoutError, OSError) as error:
            print(f"Client {address} disconnected: {error}", flush=True)


def healthcheck() -> None:
    for port in PORTS:
        with socket.create_connection(("127.0.0.1", port), timeout=2) as client:
            client.settimeout(2)
            assert client.recv(128) == b"Enter your username: "
            client.sendall(b"healthcheck\n")
            assert client.recv(128) == b"Enter your password: "
            client.sendall(b"healthcheck\n")
            assert b"stole your credentials" in client.recv(256)


def main() -> None:
    if sys.argv[1:] == ["--healthcheck"]:
        healthcheck()
        return

    with selectors.DefaultSelector() as selector:
        listeners = []
        for port in PORTS:
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("0.0.0.0", port))
            listener.listen(16)
            selector.register(listener, selectors.EVENT_READ)
            listeners.append(listener)
            print(f"Mock FTP prompt listening on port {port}...", flush=True)

        try:
            while True:
                for key, _ in selector.select():
                    client, address = key.fileobj.accept()
                    serve_client(client, address)
        finally:
            for listener in listeners:
                selector.unregister(listener)
                listener.close()


if __name__ == "__main__":
    main()

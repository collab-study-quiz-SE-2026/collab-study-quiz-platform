"""Verify local HTTPS/WSS without installing a CA into Windows trust."""

import socket
import ssl
from pathlib import Path

import httpx
from websockets.sync.client import connect


def main():
    ca_file = Path(__file__).resolve().parents[1] / ".local-certs" / "root.crt"
    context = ssl.create_default_context(cafile=str(ca_file))
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.maximum_version = ssl.TLSVersion.TLSv1_3

    with socket.create_connection(("localhost", 443), timeout=5) as connection:
        with context.wrap_socket(connection, server_hostname="localhost") as secured:
            assert secured.version() == "TLSv1.3"
            print("Certificate verified; negotiated TLSv1.3")

    with httpx.Client(verify=context, timeout=10, trust_env=False) as client:
        page = client.get("https://localhost/")
        assert page.status_code == 200 and "CSMQP" in page.text
        print("HTTPS frontend: 200")
        for path, expected in [
            ("/api/health", {"status": "ok"}),
            ("/api/health/db", {"status": "ok", "database": "connected"}),
            ("/api/health/storage", {"status": "ok", "storage": "connected"}),
        ]:
            response = client.get(f"https://localhost{path}")
            assert response.status_code == 200 and response.json() == expected
            print(f"HTTPS {path}: 200")

    with connect(
        "wss://localhost/ws/health", ssl=context,
        origin="https://localhost", open_timeout=5,
    ) as websocket:
        websocket.send("ping")
        assert websocket.recv(timeout=5) == "pong"
        print("Certificate-verified WSS: ping -> pong")

    legacy = ssl.create_default_context(cafile=str(ca_file))
    legacy.minimum_version = ssl.TLSVersion.TLSv1_2
    legacy.maximum_version = ssl.TLSVersion.TLSv1_2
    try:
        with socket.create_connection(("localhost", 443), timeout=5) as connection:
            with legacy.wrap_socket(connection, server_hostname="localhost"):
                raise AssertionError("The server accepted TLS 1.2")
    except ssl.SSLError as error:
        assert error.reason == "TLSV1_ALERT_PROTOCOL_VERSION"
        print("TLS 1.2 correctly rejected")


if __name__ == "__main__":
    main()

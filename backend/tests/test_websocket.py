import os

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from app.main import app


def test_websocket_ping_pong():
    origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    with TestClient(app) as client:
        with client.websocket_connect("/ws/health", headers={"Origin": origin}) as socket:
            for _ in range(2):
                socket.send_text("ping")
                assert socket.receive_text() == "pong"


def test_websocket_unexpected_text():
    with TestClient(app) as client:
        with client.websocket_connect("/ws/health") as socket:
            socket.send_text("hello")
            assert socket.receive_text() == "Send ping"
            socket.send_text("ping")
            assert socket.receive_text() == "pong"


def test_websocket_rejects_other_browser_origin():
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect(
                "/ws/health", headers={"Origin": "https://untrusted.example"}
            ):
                pass

    assert error.value.code == 1008

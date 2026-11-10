"""Small in-memory helpers for the live quiz WebSocket route."""

import asyncio
from time import perf_counter

from fastapi import WebSocket

ROUND_SECONDS = 30

# Rooms live only while this backend process is running. This is enough for the
# local class project; multiple server workers would need shared storage later.
rooms: dict[int, dict] = {}


async def broadcast(room: dict, message: dict) -> float:
    """Send one event to every connected socket and return elapsed milliseconds."""
    started = perf_counter()
    sockets = list(room["connections"].values())
    results = await asyncio.gather(
        *(socket.send_json(message) for socket in sockets),
        return_exceptions=True,
    )
    for socket, result in zip(sockets, results):
        if isinstance(result, Exception):
            for user_id, connected_socket in list(room["connections"].items()):
                if connected_socket is socket:
                    room["connections"].pop(user_id, None)
    return (perf_counter() - started) * 1000


async def send_error(websocket: WebSocket, message: str) -> None:
    """Send a safe, credential-free error event to one client."""
    await websocket.send_json({"type": "ERROR", "message": message})

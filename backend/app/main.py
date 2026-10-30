import os

import psycopg
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_methods=["GET"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def database_health():
    try:
        with psycopg.connect(connect_timeout=3) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="Database unavailable") from None

    return {"status": "ok", "database": "connected"}


@app.websocket("/ws/health")
async def websocket_health(websocket: WebSocket):
    origin = websocket.headers.get("origin")
    if origin is not None and origin != frontend_origin:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_text("pong")
            else:
                await websocket.send_text("Send ping")
    except WebSocketDisconnect:
        pass

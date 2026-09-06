import asyncio
from fastapi import WebSocket, WebSocketDisconnect

from backend.state_manager import StateManager


class ConnectionManager:

    def __init__(self):
        self.connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def send_state(self, websocket: WebSocket, state_manager):
        while True:
            state = state_manager.load_from_file()
            await websocket.send_json(state)
            await asyncio.sleep(0.5)


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, state_manager):
    await manager.connect(websocket)

    try:
        await send_state_loop(websocket, state_manager)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

    except Exception as e:
        print(f"[WEBSOCKET] Error: {e}")
        manager.disconnect(websocket)


async def send_state_loop(websocket, state_manager):
    while True:
        state = state_manager.load_from_file()
        await websocket.send_json(state)
        await asyncio.sleep(0.5)
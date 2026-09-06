# File: /Users/entity/Desktop/Drone_modules/backend/state_manager.py
import json
import os
import threading


class StateManager:

    def __init__(self, state_file):
        self.state_file = state_file
        self.lock = threading.Lock()
        self.state = {
            "system": "Falcon Rescue AI",
            "status": "online",
            "people": [],
            "summary": {},
            "drone_location": None,
            "qwen_vl_analysis": {},
        }

    def update(self, state):
        with self.lock:
            self.state = state

    def load_from_file(self):
        if not os.path.exists(self.state_file):
            return self.get_state()

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            with self.lock:
                self.state = data

            return data

        except (OSError, json.JSONDecodeError) as exc:
            print(f"[STATE] Error loading state: {exc}")
            return self.get_state()

    def get_state(self):
        with self.lock:
            return dict(self.state)

# File: /Users/entity/Desktop/Drone_modules/backend/main.py
# (Assuming existing imports and endpoints are preserved; only adding shared StateManager instance and endpoint if missing)

import os
from fastapi import FastAPI

app = FastAPI()

# Initialize shared StateManager instance with root project's output/rescue_state.json
state_manager = None
state_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output", "rescue_state.json"))
try:
    from .state_manager import StateManager
except ImportError:
    from state_manager import StateManager

state_manager = StateManager(state_file_path)

# Existing endpoints and imports are preserved here...

# Add /api/state endpoint if not already defined
from fastapi.routing import APIRoute

existing_routes = [route.path for route in app.routes if isinstance(route, APIRoute)]

if "/api/state" not in existing_routes:

    @app.get("/api/state")
    async def get_state():
        return state_manager.load_from_file()

# File: /Users/entity/Desktop/Drone_modules/backend/websocket.py
import asyncio
from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:

    def __init__(self):
        self.connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)


manager = ConnectionManager()


async def send_state_loop(websocket, state_manager):
    while True:
        state = state_manager.load_from_file()
        await websocket.send_json(state)
        await asyncio.sleep(0.25)


async def websocket_endpoint(websocket, state_manager):
    await manager.connect(websocket)

    try:
        await send_state_loop(websocket, state_manager)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        print(f"[WEBSOCKET] Error: {exc}")
        manager.disconnect(websocket)

# File: /Users/entity/Desktop/Drone_modules/pipeline.py
# (Only showing the relevant modifications and integration with PersonStateManager)

# At the top of the file, alongside other top-level imports:
from person_state import PersonStateManager

# Instantiate one PersonStateManager before main processing loop:
person_state = PersonStateManager()

# ... inside the main processing loop, after applying movement, pose, identity, condition, and priority fields to tracked_people for a frame:

# Example snippet where tracked_people and timestamp are available:

# After all updates to tracked_people:
person_state.update(tracked_people, timestamp)

# When constructing the people portion of the JSON state:
state_people = person_state.get_active_people()

# Then include state_people in the final state JSON under the "people" key,
# preserving all existing top-level keys like timestamp, frame, drone, scene, and others.

# For example, the final state JSON construction might look like:

state = {
    "timestamp": timestamp,
    "frame": frame_number,
    "drone": drone_info,
    "scene": scene_info,
    "people": state_people,
    # ... other existing keys ...
}

# Ensure each person in state_people retains at least:
# id, bbox, confidence, movement, posture, identity, database_id,
# identity_distance, identity_similarity, condition,
# priority, priority_score, priority_reasons, qwen_observations

# Preserve existing camera, enrollment, keyboard/operator-command, or AI functionality without modification.

# End of pipeline.py modifications.
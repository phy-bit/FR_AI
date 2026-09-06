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
            return self.state

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            with self.lock:
                self.state = data

            return data

        except Exception as e:
            print(f"[STATE] Error loading state: {e}")
            return self.state

    def get_state(self):
        with self.lock:
            return self.state.copy()
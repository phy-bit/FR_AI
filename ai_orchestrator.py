import os
import time
import json
import cv2
import numpy as np

from camera import Camera
from detector import PersonDetector
from tracker import ObjectTracker
from movement import MovementAnalyzer
from pose import PoseAnalyzer
from condition import ConditionAnalyzer
from face_database import FaceDatabase
from face_recognizer import FaceRecognizer
from face_association import associate_faces_with_people
from rescue_priority import RescuePriorityEngine


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
LIVE_FRAME = os.path.join(OUTPUT_DIR, "live_frame.jpg")
STATE_FILE = os.path.join(OUTPUT_DIR, "rescue_state.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def atomic_write_json(path, data):
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    os.replace(temp_path, path)


def run_ai_loop(stop_event):
    print("[AI] Starting Falcon AI orchestrator...")

    camera = Camera()
    detector = PersonDetector()
    tracker = ObjectTracker(detector.model)

    movement = MovementAnalyzer()
    pose = PoseAnalyzer()
    condition = ConditionAnalyzer()

    database = FaceDatabase()
    face_recognizer = FaceRecognizer(database)
    priority_engine = RescuePriorityEngine()

    print("[AI] All modules initialized.")

    camera.start()
    frame_number = 0

    try:
        while not stop_event.is_set():
            frame = camera.read()

            if frame is None:
                time.sleep(0.01)
                continue

            # Camera.read() may return (frame, metadata). Only the NumPy
            # image should be passed to detector, tracker, face recognition,
            # pose analysis, and OpenCV.
            if isinstance(frame, tuple):
                if not frame:
                    time.sleep(0.01)
                    continue
                frame = frame[0]

            if not isinstance(frame, np.ndarray):
                print(
                    f"[AI ORCHESTRATOR] Invalid camera frame: "
                    f"expected numpy.ndarray, got {type(frame).__name__}: {frame!r}"
                )
                time.sleep(0.01)
                continue

            if frame.ndim != 3 or frame.shape[2] not in (3, 4):
                print(
                    f"[AI ORCHESTRATOR] Invalid camera frame shape: {frame.shape}"
                )
                time.sleep(0.01)
                continue

            frame_number += 1

            detections = detector.detect(frame)

            tracked_objects = tracker.track(frame)
            tracked_people = [
                obj
                for obj in tracked_objects
                if obj.get("type") == "person"
            ]

            people = []

            for person in tracked_people:
                person_id = person["id"]
                bbox = person["bbox"]

                movement_result = movement.update(person_id, bbox)
                pose_result = pose.analyze(frame, bbox)
                condition_result = condition.analyze(
                    movement_result,
                    pose_result,
                    person.get("confidence", 0.0)
                )

                person_state = {
                    "id": person_id,
                    "bbox": bbox,
                    "confidence": person.get("confidence", 0.0),
                    "movement": movement_result,
                    "posture": pose_result,
                    "condition": condition_result,
                    "identity": "unknown",
                    "database_id": None,
                    "identity_distance": None,
                    "identity_similarity": 0.0
                }

                people.append(person_state)

            face_results = face_recognizer.recognize(frame)
            associations = associate_faces_with_people(
                face_results,
                people
            )

            association_by_track = {
                item["track_id"]: item
                for item in associations
            }

            for person in people:
                association = association_by_track.get(person["id"])

                if association is None:
                    continue

                person["identity"] = association.get(
                    "identity",
                    "UNKNOWN"
                )
                person["database_id"] = association.get("database_id")
                person["identity_distance"] = association.get(
                    "identity_distance"
                )
                person["identity_similarity"] = association.get(
                    "identity_similarity",
                    0.0
                )

            for person in people:
                priority = priority_engine.calculate(person)
                person["priority"] = priority.get("priority", "LOW")
                person["priority_score"] = priority.get("score", 0)
                person["priority_reasons"] = priority.get("reasons", [])

            display_frame = frame.copy()

            for person in people:
                x1, y1, x2, y2 = map(int, person["bbox"])
                label = (
                    f'{person["identity"]} '
                    f'P:{person["priority"]}'
                )

                cv2.rectangle(
                    display_frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    display_frame,
                    label,
                    (x1, max(20, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )

            temp_frame = os.path.join(OUTPUT_DIR, "live_frame.tmp.jpg")
            if not cv2.imwrite(temp_frame, display_frame):
                raise RuntimeError(f"Failed to write live frame: {temp_frame}")
            os.replace(temp_frame, LIVE_FRAME)

            state = {
                "timestamp": time.time(),
                "frame": frame_number,
                "drone": {
                    "latitude": None,
                    "longitude": None,
                    "altitude": None,
                    "heading": None
                },
                "scene": {
                    "scene": "unknown",
                    "environment": [],
                    "hazards": [],
                    "people_observations": [],
                    "possible_distress_cues": [],
                    "rescue_observations": []
                },
                "people": people,
                "qwen_vl_analysis": {}
            }

            atomic_write_json(STATE_FILE, state)
            time.sleep(0.001)

    finally:
        print("[AI] Stopping Falcon AI orchestrator...")

        try:
            camera.release()
        except Exception:
            pass

        print("[AI] Falcon AI orchestrator stopped.")
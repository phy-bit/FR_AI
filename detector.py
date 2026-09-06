from ultralytics import YOLO
import numpy as np


class PersonDetector:

    def __init__(self, model_path="yolo11n.pt"):
        self.model = YOLO(model_path)

    def detect(self, frame):
        if frame is None:
            return []

        # Camera pipelines may return (frame, metadata).
        # Extract only the actual NumPy image before inference.
        if isinstance(frame, tuple):
            if not frame:
                return []
            frame = frame[0]

        if not isinstance(frame, np.ndarray):
            raise TypeError(
                f"PersonDetector.detect() expected a numpy frame, "
                f"got {type(frame).__name__}: {frame!r}"
            )

        if frame.ndim != 3 or frame.shape[2] not in (3, 4):
            raise ValueError(
                f"PersonDetector.detect() expected a 3-channel or 4-channel image, "
                f"got shape {frame.shape}"
            )

        results = self.model(frame, verbose=False)

        detections = []

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                class_id = int(box.cls[0])

                # COCO class 0 = person.
                if class_id != 0:
                    continue

                confidence = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                detections.append({
                    "bbox": [x1, y1, x2, y2],
                    "confidence": confidence,
                    "class_id": class_id,
                    "class_name": "person"
                })

        return detections
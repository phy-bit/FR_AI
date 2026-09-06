import os
import cv2
import numpy as np
import face_recognition


class LiveIdentityManager:

    def __init__(
        self,
        database,
        required_samples=5,
        min_face_size=80,
        blur_threshold=80.0
    ):
        self.database = database

        self.required_samples = required_samples
        self.min_face_size = min_face_size
        self.blur_threshold = blur_threshold

        self.active_captures = {}

    # =========================================================
    # START CAPTURE
    # =========================================================

    def start_capture(self, track_id, name, details=None):
        """
        Start collecting face samples for a tracked person.
        """

        if not name or not name.strip():
            return {
                "success": False,
                "error": "Name is required"
            }

        if track_id in self.active_captures:
            return {
                "success": False,
                "error": "Capture already active for this person"
            }

        self.active_captures[track_id] = {
            "name": name.strip(),
            "details": details or {},
            "encodings": []
        }

        return {
            "success": True,
            "track_id": track_id,
            "name": name.strip(),
            "message": "Face capture started"
        }

        # =========================================================
    # CAPTURE STATUS
    # =========================================================

    def get_capture_status(self, track_id):

        capture = self.active_captures.get(track_id)

        if capture is None:
            return {
                "active": False,
                "track_id": track_id,
                "samples": 0,
                "required": self.required_samples
            }

        return {
            "active": True,
            "track_id": track_id,
            "name": capture["name"],
            "samples": len(capture["encodings"]),
            "required": self.required_samples
        }



    # =========================================================
    # PROCESS LIVE FRAME
    # =========================================================

    def process_frame(self, track_id, frame, bbox):
        """
        Process one live frame for the selected tracked person.

        Returns capture progress.
        """

        if track_id not in self.active_captures:
            return {
                "success": False,
                "error": "No active capture for this track"
            }

        capture = self.active_captures[track_id]

        if frame is None:
            return {
                "success": False,
                "error": "Invalid frame"
            }

        # -----------------------------------------------------
        # Crop the tracked person's region
        # -----------------------------------------------------

        x1, y1, x2, y2 = map(int, bbox)

        height, width = frame.shape[:2]

        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(width, x2)
        y2 = min(height, y2)

        if x2 <= x1 or y2 <= y1:
            return {
                "success": False,
                "error": "Invalid bounding box"
            }

        person_crop = frame[y1:y2, x1:x2]

        if person_crop.size == 0:
            return {
                "success": False,
                "error": "Empty person crop"
            }

        # -----------------------------------------------------
        # Convert BGR → RGB
        # -----------------------------------------------------

        rgb_crop = cv2.cvtColor(
            person_crop,
            cv2.COLOR_BGR2RGB
        )

        # -----------------------------------------------------
        # Find faces inside this person's bounding box
        # -----------------------------------------------------

        locations = face_recognition.face_locations(
            rgb_crop,
            model="hog"
        )

        if len(locations) == 0:
            return {
                "success": True,
                "captured": False,
                "reason": "No face detected",
                "samples": len(capture["encodings"]),
                "required": self.required_samples
            }

        # If multiple faces somehow appear inside the box,
        # choose the largest one.
        location = self._largest_face(locations)

        top, right, bottom, left = location

        face_width = right - left
        face_height = bottom - top

        # -----------------------------------------------------
        # Reject faces that are too small
        # -----------------------------------------------------

        if (
            face_width < self.min_face_size
            or face_height < self.min_face_size
        ):
            return {
                "success": True,
                "captured": False,
                "reason": "Face too small",
                "samples": len(capture["encodings"]),
                "required": self.required_samples
            }

        # -----------------------------------------------------
        # Reject blurry frames
        # -----------------------------------------------------

        face_image = rgb_crop[
            top:bottom,
            left:right
        ]

        if face_image.size == 0:
            return {
                "success": True,
                "captured": False,
                "reason": "Invalid face crop",
                "samples": len(capture["encodings"]),
                "required": self.required_samples
            }

        gray_face = cv2.cvtColor(
            face_image,
            cv2.COLOR_RGB2GRAY
        )

        blur_score = cv2.Laplacian(
            gray_face,
            cv2.CV_64F
        ).var()

        if blur_score < self.blur_threshold:
            return {
                "success": True,
                "captured": False,
                "reason": "Face too blurry",
                "samples": len(capture["encodings"]),
                "required": self.required_samples
            }

        # -----------------------------------------------------
        # Generate embedding
        # -----------------------------------------------------

        encodings = face_recognition.face_encodings(
            rgb_crop,
            [location]
        )

        if not encodings:
            return {
                "success": True,
                "captured": False,
                "reason": "Could not generate embedding",
                "samples": len(capture["encodings"]),
                "required": self.required_samples
            }

        encoding = encodings[0]
        capture["reference_frame"] = person_crop.copy()

        # -----------------------------------------------------
        # Avoid storing nearly identical consecutive frames
        # -----------------------------------------------------

        if self._too_similar(
            encoding,
            capture["encodings"]
        ):
            return {
                "success": True,
                "captured": False,
                "reason": "Frame too similar to previous sample",
                "samples": len(capture["encodings"]),
                "required": self.required_samples
            }

        # -----------------------------------------------------
        # Store embedding temporarily
        # -----------------------------------------------------

        capture["encodings"].append(encoding)

        sample_count = len(
            capture["encodings"]
        )

        # -----------------------------------------------------
        # Automatically finish after enough samples
        # -----------------------------------------------------

        if sample_count >= self.required_samples:

            result = self._finish_capture(
                track_id
            )

            return result

        return {
            "success": True,
            "captured": True,
            "reason": "Good face sample",
            "samples": sample_count,
            "required": self.required_samples,
            "complete": False
        }

    # =========================================================
    # FINISH CAPTURE
    # =========================================================

    def _finish_capture(self, track_id):

        capture = self.active_captures.get(
            track_id
        )

        if capture is None:
            return {
                "success": False,
                "error": "Capture not found"
            }

        # Generate a collision-safe person ID.
        people = self.database.get_all()

        existing_numbers = []

        for existing_id in people.keys():
            if not isinstance(existing_id, str):
                continue

            if (
                existing_id.startswith("P")
                and existing_id[1:].isdigit()
            ):
                existing_numbers.append(
                    int(existing_id[1:])
                )

        next_number = max(existing_numbers, default=0) + 1
        person_id = f"P{next_number:03d}"

        name = capture["name"]
        details = capture["details"]
        encodings = capture["encodings"]

        # Save a reference image when a usable frame was captured.
        reference_path = None
        reference_frame = capture.get("reference_frame")

        if reference_frame is not None:
            base_dir = os.path.dirname(
                os.path.abspath(__file__)
            )

            enrollment_dir = os.path.join(
                base_dir,
                "output",
                "enrollment"
            )

            os.makedirs(enrollment_dir, exist_ok=True)

            reference_path = os.path.join(
                enrollment_dir,
                f"{person_id}.jpg"
            )

            cv2.imwrite(
                reference_path,
                reference_frame
            )

        # Store first embedding as the person's record.
        self.database.add_person(
            person_id=person_id,
            name=name,
            encoding=encodings[0],
            details=details,
            image_path=reference_path
        )

        # -----------------------------------------------------
        # Store remaining embeddings
        # -----------------------------------------------------

        for encoding in encodings[1:]:
            self.database.add_encoding(
                person_id,
                encoding
            )

        # Remove active capture
        del self.active_captures[track_id]

        return {
            "success": True,
            "complete": True,
            "track_id": track_id,
            "person_id": person_id,
            "name": name,
            "samples": len(encodings),
            "message": "Person enrolled successfully"
        }

    # =========================================================
    # CANCEL CAPTURE
    # =========================================================

    def cancel_capture(self, track_id):

        if track_id in self.active_captures:
            del self.active_captures[track_id]

            return {
                "success": True,
                "message": "Capture cancelled"
            }

        return {
            "success": False,
            "error": "No active capture"
        }

    # =========================================================
    # LARGEST FACE
    # =========================================================

    def _largest_face(self, locations):

        largest = locations[0]

        largest_area = 0

        for location in locations:

            top, right, bottom, left = location

            width = right - left
            height = bottom - top

            area = width * height

            if area > largest_area:
                largest_area = area
                largest = location

        return largest

    # =========================================================
    # SIMILARITY CHECK
    # =========================================================

    def _too_similar(
        self,
        encoding,
        previous_encodings
    ):

        if not previous_encodings:
            return False

        distances = face_recognition.face_distance(
            previous_encodings,
            encoding
        )

        # If extremely similar to an existing sample,
        # don't store another nearly identical frame.
        return np.min(distances) < 0.08
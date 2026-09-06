import math


class MovementAnalyzer:

    def __init__(self):
        self.previous_positions = {}
    def update(self, person_id, bbox):
        """Compatibility wrapper for callers that use the update() API."""
        return self.analyze(person_id, bbox)

    def analyze(self, person_id, bbox):

        x1, y1, x2, y2 = bbox

        # Calculate center of bounding box
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2

        current_position = (center_x, center_y)

        # First observation
        if person_id not in self.previous_positions:

            self.previous_positions[person_id] = current_position

            return {
                "movement": "unknown",
                "speed": 0.0
            }

        previous_position = self.previous_positions[person_id]

        # Calculate pixel displacement
        distance = math.sqrt(
            (center_x - previous_position[0]) ** 2 +
            (center_y - previous_position[1]) ** 2
        )

        self.previous_positions[person_id] = current_position

        # Classify movement
        if distance < 2:
            movement = "none"

        elif distance < 10:
            movement = "low"

        else:
            movement = "high"

        return {
            "movement": movement,
            "speed": round(distance, 2)
        }
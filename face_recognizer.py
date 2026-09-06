import face_recognition


class FaceRecognizer:

    def __init__(self, database, tolerance=0.50):
        self.database = database
        self.tolerance = tolerance

    def recognize(self, image):

        locations = face_recognition.face_locations(
            image,
            model="hog"
        )

        encodings = face_recognition.face_encodings(
            image,
            locations
        )

        results = []

        people = self.database.get_all()

        for location, encoding in zip(
            locations,
            encodings
        ):

            best_match = None
            best_distance = 1.0

            # ---------------------------------------------
            # Compare against every person
            # ---------------------------------------------

            for person_id, person in people.items():

                stored_encodings = person.get(
                    "encodings",
                    []
                )

                if not stored_encodings:
                    continue

                distances = face_recognition.face_distance(
                    stored_encodings,
                    encoding
                )

                person_distance = float(
                    distances.min()
                )

                if person_distance < best_distance:
                    best_distance = person_distance
                    best_match = person

            # ---------------------------------------------
            # Determine identity
            # ---------------------------------------------

            if (
                best_match is not None
                and best_distance <= self.tolerance
            ):
                identity = best_match["name"]
                person_id = best_match["id"]
                similarity = max(
                    0.0,
                    1.0 - best_distance
                )
            else:
                identity = "UNKNOWN"
                person_id = None
                similarity = 0.0

            results.append({
                "location": location,
                "person_id": person_id,
                "identity": identity,
                "distance": round(best_distance, 4),
                "similarity": round(similarity, 4)
            })

        return results
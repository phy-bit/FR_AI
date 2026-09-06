class RescueContextBuilder:

    def __init__(self, face_database):
        self.face_database = face_database

    def build(self, people, qwen_result=None, scene=None):
        """
        Build a clean context for the conversational LLM.

        Combines tracked people, stable identities, database details,
        movement, posture, condition, rescue priority, and the latest
        operator-requested Qwen-VL scene analysis.
        """

        if qwen_result is None:
            qwen_result = {}

        if scene is None:
            scene = {}

        database_people = self.face_database.get_all()
        qwen_people = qwen_result.get(
            "people_observations",
            []
        )

        context_people = []

        for person in people:

            track_id = person.get("id")
            database_id = person.get("database_id")
            identity = person.get(
                "identity",
                "UNKNOWN"
            )

            person_context = {
                "track_id": track_id,
                "database_id": database_id,
                "identity": identity,
                "identity_similarity": person.get(
                    "identity_similarity",
                    person.get("identity_confidence", 0.0)
                ),
                "identity_distance": person.get(
                    "identity_distance"
                ),
                "movement": person.get(
                    "movement",
                    "unknown"
                ),
                "posture": person.get(
                    "posture",
                    "unknown"
                ),
                "condition": person.get(
                    "condition",
                    "unknown"
                ),
                "priority": person.get(
                    "priority",
                    "unknown"
                ),
                "priority_score": person.get(
                    "priority_score",
                    0
                )
            }

            # Prefer the stable database ID supplied by recognition.
            database_record = None

            if database_id is not None:
                database_record = database_people.get(
                    database_id
                )

            # Backward-compatible fallback for older state objects.
            if database_record is None and identity != "UNKNOWN":
                database_record = self._find_person(
                    identity,
                    database_people
                )

            if database_record is not None:

                person_context["registered_details"] = (
                    database_record.get(
                        "details",
                        {}
                    )
                )

                person_context["registered_person_id"] = (
                    database_record.get(
                        "id",
                        database_id
                    )
                )

                person_context["enrollment_image"] = (
                    database_record.get(
                        "image_path"
                    )
                )

            # Attach only observations that can be associated with
            # this tracked person. Global scene information remains
            # under qwen_vl_analysis below.
            person_observations = self._find_qwen_observations(
                track_id,
                qwen_people
            )

            if person_observations:
                person_context["qwen_observations"] = (
                    person_observations
                )

            context_people.append(
                person_context
            )

        return {
            "scene": scene,

            "qwen_vl_analysis": {
                "scene": qwen_result.get(
                    "scene",
                    {}
                ),
                "environment": qwen_result.get(
                    "environment",
                    {}
                ),
                "hazards": qwen_result.get(
                    "hazards",
                    []
                ),
                "people_observations": qwen_people,
                "possible_distress_cues": qwen_result.get(
                    "possible_distress_cues",
                    []
                ),
                "rescue_observations": qwen_result.get(
                    "rescue_observations",
                    []
                )
            },

            "people": context_people,

            "summary": {
                "people_detected": len(context_people),
                "known_people": sum(
                    1
                    for person in context_people
                    if person["identity"] != "UNKNOWN"
                ),
                "unknown_people": sum(
                    1
                    for person in context_people
                    if person["identity"] == "UNKNOWN"
                )
            }
        }

    def _find_qwen_observations(
        self,
        track_id,
        qwen_people
    ):
        """Return Qwen observations explicitly associated with track_id."""

        if not isinstance(qwen_people, list):
            return {}

        matches = []

        for observation in qwen_people:

            if not isinstance(observation, dict):
                continue

            observation_track_id = observation.get(
                "track_id"
            )

            if observation_track_id is None:
                continue

            try:
                same_track = int(observation_track_id) == int(track_id)
            except (TypeError, ValueError):
                same_track = observation_track_id == track_id

            if same_track:
                matches.append(observation)

        if not matches:
            return {}

        distress = []
        rescue = []
        hazards = []

        for observation in matches:

            for item in observation.get(
                "possible_distress_cues",
                []
            ):
                if item not in distress:
                    distress.append(item)

            for item in observation.get(
                "rescue_observations",
                []
            ):
                if item not in rescue:
                    rescue.append(item)

            for item in observation.get(
                "hazards",
                []
            ):
                if item not in hazards:
                    hazards.append(item)

        return {
            "possible_distress_cues": distress,
            "rescue_observations": rescue,
            "hazards": hazards,
            "observations": matches
        }

    def _find_person(self, identity, database_people):

        for person_id, person in database_people.items():

            if person.get("name") == identity:
                return person

        return None
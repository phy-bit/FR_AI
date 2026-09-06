def point_inside_bbox(point, bbox):

    x, y = point
    x1, y1, x2, y2 = bbox

    return (
        x1 <= x <= x2
        and y1 <= y <= y2
    )


def _bbox_area(bbox):
    x1, y1, x2, y2 = bbox
    return max(0, x2 - x1) * max(0, y2 - y1)


def _face_center_inside_ratio(face_center, bbox):
    if not point_inside_bbox(face_center, bbox):
        return 0.0

    # The face center is inside the person's box. Prefer the
    # smallest containing person box when boxes overlap.
    area = _bbox_area(bbox)
    if area <= 0:
        return 0.0

    return 1.0 / area


def associate_faces_with_people(
    face_results,
    tracked_people
):

    associations = []

    for face in face_results:

        top, right, bottom, left = face["location"]

        face_center = (
            (left + right) // 2,
            (top + bottom) // 2
        )

        best_person = None
        best_score = 0.0

        for person in tracked_people:

            score = _face_center_inside_ratio(
                face_center,
                person["bbox"]
            )

            if score > best_score:
                best_score = score
                best_person = person

        if best_person is not None:

            associations.append({
                "track_id": best_person["id"],
                "database_id": face.get("person_id"),
                "identity": face.get("identity", "UNKNOWN"),
                "identity_distance": face.get("distance"),
                "identity_similarity": face.get("similarity", 0.0),
                "face_location": face["location"]
            })

    return associations
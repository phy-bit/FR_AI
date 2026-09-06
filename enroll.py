import os
import cv2
import face_recognition
import sys

from face_database import FaceDatabase


def enroll_person(name, image_path, details=None, database=None):
    name = str(name).strip()

    if not name:
        raise ValueError("Name cannot be empty.")

    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = face_recognition.load_image_file(image_path)

    locations = face_recognition.face_locations(image)

    if len(locations) == 0:
        raise ValueError("No face found.")

    if len(locations) > 1:
        raise ValueError(
            "Multiple faces found. Please provide an image containing only the person being enrolled."
        )

    encodings = face_recognition.face_encodings(image, locations)

    if not encodings:
        raise ValueError("Could not create face embedding.")

    encoding = encodings[0]

    if database is None:
        database = FaceDatabase()

    existing_numbers = []

    for person_id in database.people.keys():
        if not isinstance(person_id, str):
            continue

        if person_id.startswith("P") and person_id[1:].isdigit():
            existing_numbers.append(int(person_id[1:]))

    next_number = max(existing_numbers, default=0) + 1
    person_id = f"P{next_number:03d}"

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

    reference_image = cv2.cvtColor(
        image,
        cv2.COLOR_RGB2BGR
    )

    if not cv2.imwrite(reference_path, reference_image):
        raise RuntimeError("Failed to save reference image.")

    database.add_person(
        person_id,
        name,
        encoding,
        details=details,
        image_path=reference_path
    )

    return {
        "id": person_id,
        "name": name,
        "reference_image": reference_path
    }


# New function: enroll_from_images
def enroll_from_images(name, image_paths, details=None, database=None):
    name = str(name).strip()

    if not name:
        raise ValueError("Name cannot be empty.")

    if not image_paths:
        raise ValueError("No enrollment images supplied.")

    if database is None:
        database = FaceDatabase()

    encodings = []
    reference_image = None

    for image_path in image_paths:
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        image = face_recognition.load_image_file(image_path)
        locations = face_recognition.face_locations(image)

        if len(locations) == 0:
            raise ValueError(
                f"No face found in enrollment image: {image_path}"
            )

        if len(locations) > 1:
            raise ValueError(
                f"Multiple faces found in enrollment image: {image_path}"
            )

        image_encodings = face_recognition.face_encodings(
            image,
            locations
        )

        if not image_encodings:
            raise ValueError(
                f"Could not create face embedding: {image_path}"
            )

        encodings.append(image_encodings[0])

        if reference_image is None:
            reference_image = image

    existing_numbers = []

    for person_id in database.people.keys():
        if not isinstance(person_id, str):
            continue

        if person_id.startswith("P") and person_id[1:].isdigit():
            existing_numbers.append(int(person_id[1:]))

    next_number = max(existing_numbers, default=0) + 1
    person_id = f"P{next_number:03d}"

    base_dir = os.path.dirname(os.path.abspath(__file__))
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

    reference_bgr = cv2.cvtColor(
        reference_image,
        cv2.COLOR_RGB2BGR
    )

    if not cv2.imwrite(reference_path, reference_bgr):
        raise RuntimeError("Failed to save reference image.")

    # Store all five embeddings when the database supports it.
    if hasattr(database, "add_person"):
        database.add_person(
            person_id,
            name,
            encodings[0],
            details=details,
            image_path=reference_path
        )

        person = database.people.get(person_id)
        if isinstance(person, dict):
            person["embeddings"] = encodings
            person["details"] = details
            person["image_path"] = reference_path

            if hasattr(database, "save"):
                database.save()
    else:
        raise RuntimeError("FaceDatabase does not support add_person().")

    return {
        "id": person_id,
        "name": name,
        "details": details or "",
        "samples": len(encodings),
        "reference_image": reference_path
    }


def main():
    if len(sys.argv) != 3:
        print("Usage: python enroll.py <name> <image>")
        sys.exit(1)

    try:
        result = enroll_person(
            sys.argv[1],
            sys.argv[2]
        )
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)

    print()
    print("[DATABASE] Person enrolled successfully.")
    print(f"ID: {result['id']}")
    print(f"Name: {result['name']}")
    print(f"Reference image: {result['reference_image']}")


if __name__ == "__main__":
    main()
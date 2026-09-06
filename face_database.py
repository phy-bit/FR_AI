import os
import pickle


class FaceDatabase:

    def __init__(self, database_file=None):

        # Always store the database relative to this file,
        # not relative to wherever Python was launched from.
        base_dir = os.path.dirname(
            os.path.abspath(__file__)
        )

        if database_file is None:
            database_file = os.path.join(
                base_dir,
                "face_database.pkl"
            )
        elif not os.path.isabs(database_file):
            database_file = os.path.join(
                base_dir,
                database_file
            )

        self.database_file = database_file

        # Folder for original enrollment photos
        self.image_directory = os.path.join(
            base_dir,
            "face_images"
        )

        os.makedirs(
            self.image_directory,
            exist_ok=True
        )

        self.people = {}

        print(
            f"[FACE DB] Database: {self.database_file}"
        )
        print(
            f"[FACE DB] Images:   {self.image_directory}"
        )

        self.load()

    # --------------------------------------------------
    # ADD NEW PERSON
    # --------------------------------------------------

    def add_person(
        self,
        person_id,
        name,
        encoding,
        details=None,
        image_path=None
    ):

        self.people[person_id] = {
            "id": person_id,
            "name": name,
            "details": details or {},
            "image_path": image_path,
            "encodings": [encoding]
        }

        self.save()

    # --------------------------------------------------
    # ADD ANOTHER EMBEDDING
    # --------------------------------------------------

    def add_encoding(self, person_id, encoding):

        if person_id not in self.people:
            return False

        self.people[person_id]["encodings"].append(
            encoding
        )

        self.save()

        return True

    # --------------------------------------------------
    # GET ALL PEOPLE
    # --------------------------------------------------

    def get_all(self):
        return self.people

    # --------------------------------------------------
    # GET ONE PERSON
    # --------------------------------------------------

    def get_person(self, person_id):
        return self.people.get(person_id)

    # --------------------------------------------------
    # SAVE DATABASE
    # --------------------------------------------------

    def save(self):

        os.makedirs(
            os.path.dirname(self.database_file),
            exist_ok=True
        )

        # Save atomically to reduce corruption risk
        temp_file = self.database_file + ".tmp"

        with open(temp_file, "wb") as file:
            pickle.dump(
                self.people,
                file,
                protocol=pickle.HIGHEST_PROTOCOL
            )

        os.replace(
            temp_file,
            self.database_file
        )

        print(
            f"[FACE DB] Saved {len(self.people)} people"
        )

    # --------------------------------------------------
    # LOAD DATABASE
    # --------------------------------------------------

    def load(self):

        if not os.path.exists(self.database_file):
            print("[FACE DB] No existing database found.")
            return

        try:

            with open(
                self.database_file,
                "rb"
            ) as file:

                self.people = pickle.load(file)

            print(
                f"[FACE DB] Loaded {len(self.people)} people"
            )

            for person_id, person in self.people.items():

                encoding_count = len(
                    person.get("encodings", [])
                )

                print(
                    f"[FACE DB] "
                    f"{person_id}: "
                    f"{person.get('name', 'UNKNOWN')} "
                    f"({encoding_count} embeddings)"
                )

        except Exception as error:

            print(
                f"[FACE DB] Failed to load database: {error}"
            )

            self.people = {}
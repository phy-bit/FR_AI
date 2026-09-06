class ObjectTracker:

    def __init__(self, model):
        self.model = model

    def track(self, frame):

        results = self.model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=0.40,
            verbose=False
        )

        result = results[0]

        tracked_objects = []

        if result.boxes.id is None:
            return tracked_objects

        boxes = result.boxes.xyxy.cpu().numpy()
        ids = result.boxes.id.cpu().numpy()
        confidences = result.boxes.conf.cpu().numpy()
        class_ids = result.boxes.cls.cpu().numpy()

        for box, track_id, confidence, class_id in zip(
            boxes,
            ids,
            confidences,
            class_ids
        ):

            x1, y1, x2, y2 = map(int, box)

            track_id = int(track_id)
            class_id = int(class_id)

            class_name = self.model.names[class_id]

            if class_name == "person":
                object_type = "person"
            else:
                object_type = "object"

            tracked_objects.append({
                "id": track_id,
                "class_id": class_id,
                "class_name": class_name,
                "type": object_type,
                "bbox": [x1, y1, x2, y2],
                "confidence": float(confidence)
            })

        return tracked_objects
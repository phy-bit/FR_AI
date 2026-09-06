from ultralytics import YOLO


class PoseAnalyzer:

    def __init__(self, model_path="yolo11n-pose.pt"):
        self.model = YOLO(model_path)

    def analyze(self, frame, person_bbox):

        results = self.model(
            frame,
            classes=[0],
            conf=0.35,
            verbose=False
        )

        best_pose = None
        best_iou = 0.0
        best_keypoint_conf = None

        for result in results:

            if result.boxes is None or result.keypoints is None:
                continue

            for i, box in enumerate(result.boxes.xyxy):

                pose_bbox = box.cpu().numpy()

                iou = self._calculate_iou(
                    person_bbox,
                    pose_bbox
                )

                if iou <= best_iou:
                    continue

                keypoints = result.keypoints.xy[i].cpu().numpy()

                keypoint_conf = None
                if getattr(result.keypoints, "conf", None) is not None:
                    keypoint_conf = (
                        result.keypoints.conf[i]
                        .cpu()
                        .numpy()
                    )

                best_iou = iou
                best_pose = keypoints
                best_keypoint_conf = keypoint_conf

        if best_pose is None or best_iou < 0.20:
            return {
                "posture": "unknown",
                "keypoints": None
            }

        posture = self._classify_posture(
            best_pose,
            best_keypoint_conf
        )

        return {
            "posture": posture,
            "keypoints": best_pose.tolist()
        }

    # -----------------------------------------
    # IOU
    # -----------------------------------------

    def _calculate_iou(self, box1, box2):

        x1, y1, x2, y2 = box1
        a1, b1, a2, b2 = box2

        intersection_x1 = max(x1, a1)
        intersection_y1 = max(y1, b1)
        intersection_x2 = min(x2, a2)
        intersection_y2 = min(y2, b2)

        width = max(0, intersection_x2 - intersection_x1)
        height = max(0, intersection_y2 - intersection_y1)

        intersection = width * height

        area1 = max(0, x2 - x1) * max(0, y2 - y1)
        area2 = max(0, a2 - a1) * max(0, b2 - b1)

        union = area1 + area2 - intersection

        if union == 0:
            return 0.0

        return intersection / union

    # -----------------------------------------
    # POSTURE CLASSIFICATION
    # -----------------------------------------

    def _classify_posture(self, kp, conf=None):

        # YOLO pose keypoints:
        # 5  = left shoulder
        # 6  = right shoulder
        # 11 = left hip
        # 12 = right hip
        # 15 = left ankle
        # 16 = right ankle

        required = [5, 6, 11, 12, 15, 16]

        if conf is not None:
            for index in required:
                if index >= len(conf) or float(conf[index]) < 0.30:
                    return "unknown"

        left_shoulder = kp[5]
        right_shoulder = kp[6]
        left_hip = kp[11]
        right_hip = kp[12]
        left_ankle = kp[15]
        right_ankle = kp[16]

        shoulder = (
            (left_shoulder[0] + right_shoulder[0]) / 2,
            (left_shoulder[1] + right_shoulder[1]) / 2
        )

        hip = (
            (left_hip[0] + right_hip[0]) / 2,
            (left_hip[1] + right_hip[1]) / 2
        )

        ankle = (
            (left_ankle[0] + right_ankle[0]) / 2,
            (left_ankle[1] + right_ankle[1]) / 2
        )

        torso_dx = abs(hip[0] - shoulder[0])
        torso_dy = abs(hip[1] - shoulder[1])

        # -----------------------------------------
        # LYING
        # -----------------------------------------

        if torso_dx > torso_dy * 1.5:
            return "lying"

        # -----------------------------------------
        # STANDING
        # -----------------------------------------

        if (
            torso_dy > torso_dx * 1.5
            and ankle[1] > hip[1]
        ):
            return "standing"

        # -----------------------------------------
        # SITTING
        # -----------------------------------------

        if (
            torso_dy > torso_dx
            and ankle[1] > hip[1]
        ):
            return "sitting"

        return "unknown"
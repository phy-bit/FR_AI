import cv2
import time
import os


class Camera:

    def __init__(
        self,
        source=0,
        width=1280,
        height=720,
        fps=30,
        recording=False,
        output_dir="recordings"
    ):

        self.source = source
        self.width = width
        self.height = height
        self.target_fps = fps
        self.recording = recording
        self.output_dir = output_dir

        self.cap = None
        self.writer = None

        self.start_time = None
        self.frame_count = 0

    def start(self):
        self.cap = cv2.VideoCapture(self.source)

        if not self.cap.isOpened():
            raise RuntimeError(
                f"Could not open camera/source: {self.source}"
            )

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        self.start_time = time.time()
        self.frame_count = 0

        if self.recording:
            self._start_recording()

    def _start_recording(self):
        os.makedirs(self.output_dir, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        filename = os.path.join(
            self.output_dir,
            f"rescue_{timestamp}.mp4"
        )

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        self.writer = cv2.VideoWriter(
            filename,
            fourcc,
            self.target_fps,
            (self.width, self.height)
        )

        print(f"[CAMERA] Recording: {filename}")

    def read(self):
        if self.cap is None:
            raise RuntimeError(
                "Camera has not been started."
            )

        ret, frame = self.cap.read()

        if not ret or frame is None:
            return None, None

        self.frame_count += 1

        timestamp = time.time() - self.start_time

        if self.writer is not None:
            self.writer.write(frame)

        return frame, timestamp

    def is_running(self):
        return (
            self.cap is not None
            and self.cap.isOpened()
        )

    def stop(self):
        if self.writer is not None:
            self.writer.release()
            self.writer = None

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        print("[CAMERA] Stopped.")

    def __del__(self):
        try:
            self.stop()
        except Exception:
            pass
import asyncio
import cv2
import os

from fastapi import WebSocket, WebSocketDisconnect


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "output"
)

PHONE_FRAME = os.path.join(
    OUTPUT_DIR,
    "phone_frame.jpg"
)

PHONE_FRAME_TMP = PHONE_FRAME + ".tmp"


os.makedirs(OUTPUT_DIR, exist_ok=True)


class PhoneCameraBridge:

    def __init__(self):
        self.connected = False
        self.last_frame_time = 0.0
        self.lock = asyncio.Lock()

    def get_latest_frame(self):
        """Return the latest phone-camera JPEG as an OpenCV BGR frame."""
        if not self.connected:
            return None

        if not os.path.exists(PHONE_FRAME):
            return None

        frame = cv2.imread(PHONE_FRAME)
        return frame

    async def receive(self, websocket: WebSocket):

        await websocket.accept()

        self.connected = True

        print("[PHONE CAMERA] Connected.")

        try:

            while True:

                data = await websocket.receive_bytes()

                if not data:
                    continue

                # Atomic replacement prevents the pipeline
                # from reading a partially-written JPEG.
                with open(
                    PHONE_FRAME_TMP,
                    "wb"
                ) as f:
                    f.write(data)

                os.replace(
                    PHONE_FRAME_TMP,
                    PHONE_FRAME
                )

                self.last_frame_time = (
                    asyncio.get_running_loop().time()
                )

        except WebSocketDisconnect:

            print(
                "[PHONE CAMERA] Disconnected."
            )

        except Exception as exc:

            print(
                f"[PHONE CAMERA] Error: {exc}"
            )

        finally:

            self.connected = False

            try:
                if os.path.exists(
                    PHONE_FRAME_TMP
                ):
                    os.remove(
                        PHONE_FRAME_TMP
                    )
            except OSError:
                pass


phone_camera = PhoneCameraBridge()
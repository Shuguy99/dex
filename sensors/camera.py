import logging
import threading
from typing import Any

logger = logging.getLogger("dex.sensors.camera")


class Camera:
    def __init__(self) -> None:
        self._capture = None
        self._active = False
        self._privacy_mode = False
        self._thread: threading.Thread | None = None

    @property
    def available(self) -> bool:
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            ret = cap.isOpened()
            cap.release()
            return ret
        except Exception:
            return False

    def start(self):
        if self._privacy_mode:
            logger.warning("Camera blocked by privacy mode")
            return False
        try:
            import cv2
            self._capture = cv2.VideoCapture(0)
            if not self._capture.isOpened():
                logger.error("Cannot open camera")
                return False
            self._active = True
            logger.info("Camera started")
            return True
        except Exception as e:
            logger.error(f"Camera start failed: {e}")
            return False

    def stop(self):
        self._active = False
        if self._capture:
            self._capture.release()
            self._capture = None
        logger.info("Camera stopped")

    def capture_frame(self) -> Any | None:
        if not self._active or self._privacy_mode:
            return None
        try:
            ret, frame = self._capture.read()
            if ret:
                return frame
            return None
        except Exception as e:
            logger.error(f"Frame capture failed: {e}")
            return None

    def detect_faces(self, frame) -> list[dict[str, Any]]:
        try:
            import face_recognition
            rgb = frame[:, :, ::-1]
            locations = face_recognition.face_locations(rgb)
            encodings = face_recognition.face_encodings(rgb, locations)
            faces = []
            for i, (top, right, bottom, left) in enumerate(locations):
                faces.append({
                    "location": {"top": top, "right": right, "bottom": bottom, "left": left},
                    "encoding": encodings[i].tolist() if i < len(encodings) else None
                })
            return faces
        except Exception as e:
            logger.error(f"Face detection failed: {e}")
            return []

    def enable_privacy_mode(self):
        self._privacy_mode = True
        self.stop()

    def disable_privacy_mode(self):
        self._privacy_mode = False

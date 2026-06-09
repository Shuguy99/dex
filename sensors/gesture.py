import logging
import time
from collections.abc import Callable

logger = logging.getLogger("dex.sensors.gesture")


class GestureController:
    def __init__(self) -> None:
        self._active = False
        self._on_gesture: dict[str, Callable] = {}
        self._last_gesture = ""
        self._gesture_cooldown = 1.0
        self._last_gesture_time = 0.0

    @property
    def available(self) -> bool:
        try:
            import cv2
            import mediapipe
            return True
        except ImportError:
            return False

    def register(self, gesture_name: str, callback: Callable) -> None:
        self._on_gesture[gesture_name] = callback
        logger.info(f"Gesture registered: {gesture_name}")

    def start(self) -> None:
        if not self.available:
            logger.warning("Gesture control requires cv2 + mediapipe")
            return
        self._active = True
        logger.info("Gesture controller started")

    def stop(self) -> None:
        self._active = False
        logger.info("Gesture controller stopped")

    def process_frame(self, frame) -> str | None:
        if not self._active:
            return None
        try:
            import cv2
            import mediapipe as mp

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_hands = mp.solutions.hands
            with mp_hands.Hands(min_detection_confidence=0.7,
                                min_tracking_confidence=0.5) as hands:
                results = hands.process(rgb)

                if not results.multi_hand_landmarks:
                    return None

                gesture = self._classify_gesture(results)
                if gesture and gesture != self._last_gesture:
                    now = time.time()
                    if now - self._last_gesture_time >= self._gesture_cooldown:
                        self._last_gesture = gesture
                        self._last_gesture_time = now
                        logger.info(f"Gesture detected: {gesture}")
                        if gesture in self._on_gesture:
                            self._on_gesture[gesture]()
                        return gesture
                return gesture

        except Exception as e:
            logger.error(f"Gesture processing error: {e}")
            return None

    def _classify_gesture(self, hand_results) -> str | None:
        try:
            import mediapipe as mp
            for hand_landmarks in hand_results.multi_hand_landmarks:
                landmarks = hand_landmarks.landmark

                thumb_tip = landmarks[mp.solutions.hands.HandLandmark.THUMB_TIP]
                index_tip = landmarks[mp.solutions.hands.HandLandmark.INDEX_FINGER_TIP]
                middle_tip = landmarks[mp.solutions.hands.HandLandmark.MIDDLE_FINGER_TIP]
                ring_tip = landmarks[mp.solutions.hands.HandLandmark.RING_FINGER_TIP]
                pinky_tip = landmarks[mp.solutions.hands.HandLandmark.PINKY_TIP]

                index_mcp = landmarks[mp.solutions.hands.HandLandmark.INDEX_FINGER_MCP]
                landmarks[mp.solutions.hands.HandLandmark.WRIST]

                fingers_up = 0
                if thumb_tip.x < index_mcp.x:
                    fingers_up += 1
                if index_tip.y < index_mcp.y:
                    fingers_up += 1
                if middle_tip.y < index_mcp.y:
                    fingers_up += 1
                if ring_tip.y < index_mcp.y:
                    fingers_up += 1
                if pinky_tip.y < index_mcp.y:
                    fingers_up += 1

                if fingers_up == 0:
                    return "fist"
                elif fingers_up == 1 and index_tip.y < index_mcp.y:
                    return "point"
                elif fingers_up == 2 and index_tip.y < index_mcp.y and middle_tip.y < index_mcp.y:
                    return "peace"
                elif fingers_up == 5:
                    return "palm"
                elif fingers_up == 3:
                    return "three"

                return None
        except Exception:
            return None

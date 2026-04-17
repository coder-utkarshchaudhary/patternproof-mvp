import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent.parent / "models" / "dark_patterns.pt"

# Maps YOLO class indices to dark pattern types
CLASS_NAMES = [
    "countdown_timer",
    "fake_scarcity",
    "confirmshaming",
    "preselection",
    "disguised_ad",
    "hidden_cost",
    "trick_question",
    "fake_social_proof",
    "fake_activity",
    "visual_interference",
    "forced_enrollment",
    "limited_time_message",
    "low_stock_message",
    "high_demand_message",
    "hard_to_cancel",
]


class DarkPatternDetector:
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        if MODEL_PATH.exists():
            try:
                from ultralytics import YOLO

                self.model = YOLO(str(MODEL_PATH))
                logger.info("YOLO model loaded from %s", MODEL_PATH)
            except Exception:
                logger.warning("Failed to load YOLO model; running in stub mode")
        else:
            logger.warning("No model at %s; running in stub mode", MODEL_PATH)

    def detect(self, image: Image.Image) -> list[dict]:
        if self.model is None:
            return []

        results = self.model(image, verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                cls_idx = int(box.cls[0])
                detections.append(
                    {
                        "class": CLASS_NAMES[cls_idx] if cls_idx < len(CLASS_NAMES) else "unknown",
                        "confidence": round(float(box.conf[0]), 4),
                        "bbox": {
                            "x1": round(float(box.xyxy[0][0]), 1),
                            "y1": round(float(box.xyxy[0][1]), 1),
                            "x2": round(float(box.xyxy[0][2]), 1),
                            "y2": round(float(box.xyxy[0][3]), 1),
                        },
                    }
                )
        return detections

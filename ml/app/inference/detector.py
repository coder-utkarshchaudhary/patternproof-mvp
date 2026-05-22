import logging
import os
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

MODEL_PATH = Path(
    os.getenv("PP_YOLO_WEIGHTS", str(Path(__file__).parent.parent / "models" / "dark_patterns.pt"))
)
CONF_THRESHOLD = float(os.getenv("PP_YOLO_CONF", "0.25"))

# Canonical YOLO class label set. These names match the granular DPType values
# in the backend taxonomy (app/models/taxonomy.py) so detections map straight
# through. Dataset labels are remapped onto this set in training/data_prep.py.
CLASS_NAMES = [
    "countdown_timer",
    "limited_time_message",
    "low_stock_message",
    "high_demand_message",
    "confirmshaming",
    "visual_interference",
    "trick_question",
    "disguised_ad",
    "preselection",
    "forced_enrollment",
    "fake_activity",
    "fake_testimonial",
    "hidden_costs",
    "hard_to_cancel",
]


class DarkPatternDetector:
    def __init__(self):
        self.model = None
        self._load_model()

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    def _load_model(self):
        if MODEL_PATH.exists():
            try:
                from ultralytics import YOLO

                self.model = YOLO(str(MODEL_PATH))
                logger.info("YOLO model loaded from %s", MODEL_PATH)
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to load YOLO model (%s); running in stub mode", e)
        else:
            logger.warning("No model at %s; running in stub mode", MODEL_PATH)

    def detect(self, image: Image.Image) -> list[dict]:
        """Return a list of {class, confidence, bbox} detections (empty if stubbed)."""
        if self.model is None:
            return []

        results = self.model(image, verbose=False, conf=CONF_THRESHOLD)
        detections = []
        for r in results:
            names = r.names if hasattr(r, "names") else {}
            for box in r.boxes:
                cls_idx = int(box.cls[0])
                label = names.get(cls_idx) if names else None
                if not label:
                    label = CLASS_NAMES[cls_idx] if cls_idx < len(CLASS_NAMES) else "unknown"
                detections.append(
                    {
                        "class": label,
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

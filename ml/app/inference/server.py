"""Pattern Proof ML inference service — YOLO dark-pattern detection.

Pure computer-vision detector. Human-readable explanations are produced by the
backend (Claude vision), so this service stays a thin, GPU-friendly /detect
endpoint with no LLM dependencies.
"""

import io
import logging

from fastapi import FastAPI, File, UploadFile
from PIL import Image

from ml.app.inference.detector import DarkPatternDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Pattern Proof ML Inference", version="0.1.0")

detector = DarkPatternDetector()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ml-inference", "model_loaded": detector.is_loaded}


@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    detections = detector.detect(image)
    return {"detections": detections}

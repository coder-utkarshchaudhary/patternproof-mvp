import io
import logging

from fastapi import FastAPI, File, UploadFile
from PIL import Image

from inference.detector import DarkPatternDetector
from inference.vlm_explainer import VLMExplainer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Pattern Proof ML Inference", version="0.1.0")

detector = DarkPatternDetector()
explainer = VLMExplainer()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ml-inference"}


@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    detections = detector.detect(image)
    return {"detections": detections}


@app.post("/explain")
async def explain(file: UploadFile = File(...), dp_class: str = "unknown"):
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    result = await explainer.explain(image, dp_class)
    return result

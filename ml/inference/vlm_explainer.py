import io
import logging

import httpx
from PIL import Image

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://ollama:11434"
VLM_MODEL = "llava"

EXPLAIN_PROMPT = """You are a dark pattern expert analyzing a UI screenshot.

A dark pattern of type "{dp_class}" was detected in this region of a webpage.

Analyze this image and provide:
1. **What it is**: A brief factual description of the UI element.
2. **Why it's a dark pattern**: Explain the deceptive design technique being used.
3. **User impact**: How this pattern manipulates or harms users.
4. **Severity**: Rate as LOW, MEDIUM, or HIGH with justification.

Be concise and factual. Do not speculate beyond what is visible."""


class VLMExplainer:
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = VLM_MODEL):
        self.base_url = base_url
        self.model = model

    async def explain(self, image: Image.Image, dp_class: str) -> dict:
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        image_bytes = buf.getvalue()

        import base64

        image_b64 = base64.b64encode(image_bytes).decode()

        prompt = EXPLAIN_PROMPT.format(dp_class=dp_class)

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "images": [image_b64],
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "explanation": data.get("response", ""),
                    "dp_class": dp_class,
                }
        except Exception as e:
            logger.error("VLM explanation failed: %s", e)
            return {
                "explanation": f"Detection: {dp_class} (explanation unavailable)",
                "dp_class": dp_class,
            }

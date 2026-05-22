"""Fine-tune a YOLO detector on the prepared dark-pattern dataset (PyTorch).

Trains from a pretrained YOLO checkpoint and copies the best weights to
``models/dark_patterns.pt`` so the inference service picks them up.

Usage:
    python train_yolo.py --data datasets/dark_patterns/dark_patterns.yaml \\
        --base yolo11s.pt --epochs 100 --imgsz 1280 --batch 8
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

MODELS_DIR = Path(__file__).parent.parent / "models"
WEIGHTS_OUT = MODELS_DIR / "dark_patterns.pt"


def train(data: Path, base: str, epochs: int, imgsz: int, batch: int, device: str | None) -> None:
    from ultralytics import YOLO

    model = YOLO(base)
    results = model.train(
        data=str(data),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project="runs/dark_patterns",
        name="train",
        exist_ok=True,
    )

    # Locate best.pt from the run and publish it to models/dark_patterns.pt.
    save_dir = Path(getattr(results, "save_dir", "runs/dark_patterns/train"))
    best = save_dir / "weights" / "best.pt"
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if best.exists():
        shutil.copy2(best, WEIGHTS_OUT)
        print(f"Published best weights -> {WEIGHTS_OUT}")
    else:
        print(f"WARNING: best.pt not found at {best}")

    # Report validation metrics for the certification claim.
    metrics = model.val(data=str(data))
    print(f"Validation mAP50-95: {getattr(metrics.box, 'map', 'n/a')}")
    print(f"Validation mAP50:    {getattr(metrics.box, 'map50', 'n/a')}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Train YOLO dark-pattern detector")
    ap.add_argument("--data", type=Path, default=Path("datasets/dark_patterns/dark_patterns.yaml"))
    ap.add_argument("--base", default="yolo11s.pt", help="pretrained base checkpoint")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--imgsz", type=int, default=1280, help="large for full-page screenshots")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--device", default=None, help="e.g. '0' for GPU, 'cpu'")
    args = ap.parse_args()
    train(args.data, args.base, args.epochs, args.imgsz, args.batch, args.device)


if __name__ == "__main__":
    main()

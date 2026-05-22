"""Dataset preparation for dark-pattern detection.

Public sources (used as-is):
  - AidUI / ContextDP — UI dark-pattern benchmark
  - arXiv dark-pattern YOLO datasets

These ship in mixed formats with their own label vocabularies. This script
remaps their labels onto Pattern Proof's canonical class set (see
``inference.detector.CLASS_NAMES``), splits into train/val/test, writes the
YOLO directory layout, and emits ``dark_patterns.yaml`` for training.

Input layout expected (per source, passed via --src):
    <src>/images/*.{jpg,png}
    <src>/labels/*.txt          # YOLO format: "<label> cx cy w h" (label may be
                                #   a class NAME or an integer index)
    <src>/classes.txt           # optional: index -> source label name, one per line

Usage:
    python data_prep.py --src datasets/raw/aidui --src datasets/raw/arxiv \\
        --out datasets/dark_patterns --val 0.15 --test 0.10
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from ml.app.inference.detector import CLASS_NAMES  # noqa: E402

CLASS_INDEX = {name: i for i, name in enumerate(CLASS_NAMES)}

# Map heterogeneous public-dataset label names onto our canonical classes.
# Extend as new datasets are added; unmapped labels are skipped (and reported).
LABEL_MAP: dict[str, str] = {
    # urgency / scarcity
    "countdown": "countdown_timer",
    "countdown_timer": "countdown_timer",
    "timer": "countdown_timer",
    "limited_time": "limited_time_message",
    "limited_time_message": "limited_time_message",
    "low_stock": "low_stock_message",
    "scarcity": "low_stock_message",
    "fake_scarcity": "low_stock_message",
    "low_stock_message": "low_stock_message",
    "high_demand": "high_demand_message",
    "high_demand_message": "high_demand_message",
    # misdirection / interface
    "confirmshaming": "confirmshaming",
    "confirm_shaming": "confirmshaming",
    "visual_interference": "visual_interference",
    "interface_interference": "visual_interference",
    "trick_question": "trick_question",
    "trickquestion": "trick_question",
    "disguised_ad": "disguised_ad",
    "disguised_advertisement": "disguised_ad",
    "ad": "disguised_ad",
    # forced action
    "preselection": "preselection",
    "pre_selection": "preselection",
    "forced_enrollment": "forced_enrollment",
    "forced_action": "forced_enrollment",
    # social proof
    "fake_activity": "fake_activity",
    "social_proof": "fake_activity",
    "fake_social_proof": "fake_activity",
    "fake_testimonial": "fake_testimonial",
    "testimonial": "fake_testimonial",
    # sneaking / obstruction
    "hidden_cost": "hidden_costs",
    "hidden_costs": "hidden_costs",
    "drip_pricing": "hidden_costs",
    "hard_to_cancel": "hard_to_cancel",
    "obstruction": "hard_to_cancel",
}


def _load_source_classes(src: Path) -> list[str] | None:
    cls_file = src / "classes.txt"
    if cls_file.exists():
        return [ln.strip() for ln in cls_file.read_text().splitlines() if ln.strip()]
    return None


def _canonical_label(token: str, src_classes: list[str] | None) -> str | None:
    """Resolve a label token (name or numeric index) to a canonical class name."""
    name = token
    if token.isdigit() and src_classes is not None:
        idx = int(token)
        if 0 <= idx < len(src_classes):
            name = src_classes[idx]
    return LABEL_MAP.get(name.strip().lower())


def _convert_label_file(label_file: Path, src_classes: list[str] | None) -> list[str] | None:
    """Rewrite one YOLO label file onto canonical class indices."""
    out_lines: list[str] = []
    for line in label_file.read_text().splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        canon = _canonical_label(parts[0], src_classes)
        if canon is None:
            continue
        out_lines.append(" ".join([str(CLASS_INDEX[canon]), *parts[1:5]]))
    return out_lines or None


def prepare(sources: list[Path], out: Path, val: float, test: float, seed: int) -> None:
    random.seed(seed)
    for split in ("train", "val", "test"):
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)

    pairs: list[tuple[Path, list[str]]] = []
    skipped = 0
    for src in sources:
        src_classes = _load_source_classes(src)
        for img in sorted((src / "images").glob("*")):
            if img.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                continue
            label_file = src / "labels" / f"{img.stem}.txt"
            if not label_file.exists():
                skipped += 1
                continue
            converted = _convert_label_file(label_file, src_classes)
            if converted is None:
                skipped += 1
                continue
            pairs.append((img, converted))

    random.shuffle(pairs)
    n = len(pairs)
    n_test = int(n * test)
    n_val = int(n * val)
    buckets = {
        "test": pairs[:n_test],
        "val": pairs[n_test : n_test + n_val],
        "train": pairs[n_test + n_val :],
    }

    for split, items in buckets.items():
        for img, lines in items:
            shutil.copy2(img, out / "images" / split / img.name)
            (out / "labels" / split / f"{img.stem}.txt").write_text("\n".join(lines))

    yaml_path = out / "dark_patterns.yaml"
    yaml_path.write_text(
        yaml.safe_dump(
            {
                "path": str(out.resolve()),
                "train": "images/train",
                "val": "images/val",
                "test": "images/test",
                "names": {i: n for i, n in enumerate(CLASS_NAMES)},
            },
            sort_keys=False,
        )
    )
    print(
        f"Prepared {n} labeled images "
        f"(train={len(buckets['train'])}, val={len(buckets['val'])}, test={len(buckets['test'])}), "
        f"skipped {skipped}. Wrote {yaml_path}"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Prepare dark-pattern YOLO dataset")
    ap.add_argument("--src", action="append", required=True, type=Path, help="raw dataset dir (repeatable)")
    ap.add_argument("--out", type=Path, default=Path("datasets/dark_patterns"))
    ap.add_argument("--val", type=float, default=0.15)
    ap.add_argument("--test", type=float, default=0.10)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    prepare(args.src, args.out, args.val, args.test, args.seed)


if __name__ == "__main__":
    main()

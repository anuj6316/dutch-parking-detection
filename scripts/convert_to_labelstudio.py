#!/usr/bin/env python3
"""
Convert YOLO polygon annotations to Label Studio JSON format
=========================================================
Processes all images and creates import JSON with polygon predictions.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scripts/labelstudio-conversion.log"),
    ],
)
logger = logging.getLogger(__name__)


class YOLOToLabelStudioConverter:
    def __init__(self, images_dir: str, labels_dir: str, output_file: str):
        self.images_dir = Path(images_dir)
        self.labels_dir = Path(labels_dir)
        self.output_file = Path(output_file)

        self.processed_count = 0
        self.error_count = 0
        self.skipped_count = 0

    def _read_yolo_label(self, label_file: Path) -> List[Dict]:
        """Read YOLO polygon labels from file."""
        polygons = []

        if not label_file.exists():
            logger.warning(f"Label file not found: {label_file.name}")
            return polygons

        with open(label_file, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                if not line or "|" in line:
                    continue

                try:
                    parts = line.split()
                    class_id = int(parts[0])
                    coords = [float(x) for x in parts[1:]]

                    if len(coords) >= 8 and len(coords) % 2 == 0:
                        polygons.append({"class_id": class_id, "coords": coords})
                        logger.debug(f"  Polygon {len(polygons)}: {len(coords)} points")
                    else:
                        logger.warning(
                            f"  Invalid polygon at line {line_num}: {len(coords)} coords"
                        )

                except Exception as e:
                    logger.error(f"  Error parsing line {line_num}: {e}")

        return polygons

    def _convert_to_labelstudio_format(
        self, image_filename: str, polygons: List[Dict]
    ) -> Dict:
        """Convert YOLO annotations to Label Studio JSON format."""

        img_width, img_height = 1536, 1536

        results = []

        for idx, polygon in enumerate(polygons, 1):
            points = []
            normalized_coords = polygon["coords"]

            for i in range(0, len(normalized_coords), 2):
                x_norm = normalized_coords[i]
                y_norm = normalized_coords[i + 1]

                x_pct = x_norm * 100
                y_pct = y_norm * 100

                points.append([x_pct, y_pct])

            logger.debug(f"  Polygon {idx}: {len(points)} points, sample: {points[0]}")

            result = {
                "type": "polygonlabels",
                "from_name": "label",
                "to_name": "image",
                "original_width": img_width,
                "original_height": img_height,
                "value": {"points": points, "polygonlabels": ["Parking"]},
            }
            results.append(result)

        task = {
            "data": {"image": f"/data/upload/dataset-for-viz/{image_filename}"},
            "predictions": [{"model_version": "yolo_obb", "result": results}],
        }

        return task

    def process_all(self) -> None:
        """Process all images and create Label Studio JSON file."""
        logger.info("=" * 60)
        logger.info("Starting YOLO to Label Studio conversion")
        logger.info("=" * 60)

        image_files = sorted(list(self.images_dir.glob("*.png")))

        logger.info(f"Found {len(image_files)} images to process")
        logger.info(f"Images directory: {self.images_dir}")
        logger.info(f"Labels directory: {self.labels_dir}")
        logger.info("")

        all_tasks = []

        for idx, img_path in enumerate(image_files, 1):
            img_filename = img_path.name
            label_path = self.labels_dir / f"{img_path.stem}.txt"

            logger.info(f"[{idx}/{len(image_files)}] Processing: {img_filename}")

            polygons = self._read_yolo_label(label_path)

            if not polygons:
                logger.warning(f"  No polygons found, skipping")
                self.skipped_count += 1
                continue

            logger.info(f"  Found {len(polygons)} polygons")

            try:
                task = self._convert_to_labelstudio_format(img_filename, polygons)
                all_tasks.append(task)
                self.processed_count += 1

                if idx <= 3:
                    self._log_sample_output(task)

            except Exception as e:
                logger.error(f"  Error converting: {e}")
                self.error_count += 1

        logger.info("")
        logger.info("=" * 60)
        logger.info("Writing output JSON file...")

        with open(self.output_file, "w") as f:
            json.dump(all_tasks, f, indent=2)

        logger.info(f"Output written to: {self.output_file}")
        logger.info(
            f"File size: {self.output_file.stat().st_size / 1024 / 1024:.2f} MB"
        )

        logger.info("")
        logger.info("=" * 60)
        logger.info("CONVERSION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total images processed: {len(image_files)}")
        logger.info(f"Successfully converted: {self.processed_count}")
        logger.info(f"Skipped (no labels): {self.skipped_count}")
        logger.info(f"Errors: {self.error_count}")
        logger.info(f"Total tasks in JSON: {len(all_tasks)}")
        logger.info("=" * 60)

    def _log_sample_output(self, task: Dict) -> None:
        """Log sample of converted task for verification."""
        logger.info(f"  Sample task structure:")
        logger.info(f"    Image: {task['data']['image']}")

        results = task["predictions"][0]["result"]
        logger.info(f"    Number of polygons: {len(results)}")

        if results:
            first_result = results[0]
            points = first_result["value"]["points"]
            logger.info(f"    First polygon points (first 3): {points[:3]}")
            logger.info(f"    First polygon total points: {len(points)}")


def main():
    base_dir = Path(__file__).parent.parent

    images_dir = base_dir / "dataset" / "dataset-for-viz" / "images"
    labels_dir = base_dir / "dataset" / "dataset-for-viz" / "labels"
    output_file = base_dir / "scripts" / "labelstudio-import.json"

    logger.info(f"Base directory: {base_dir}")
    logger.info(f"Images: {images_dir}")
    logger.info(f"Labels: {labels_dir}")
    logger.info(f"Output: {output_file}")

    converter = YOLOToLabelStudioConverter(
        images_dir=str(images_dir),
        labels_dir=str(labels_dir),
        output_file=str(output_file),
    )

    converter.process_all()


if __name__ == "__main__":
    main()

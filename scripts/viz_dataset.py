#!/usr/bin/env python3
"""
Dataset Visualization with Green Overlay
=========================================
Iteratively loads images and overlays polygon labels in green.

Usage:
    python scripts/viz_dataset.py
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatasetVisualizer:
    def __init__(self, 
                 images_dir: str, 
                 labels_dir: str, 
                 output_dir: str,
                 fill_color: str = "#22c55e",
                 alpha: float = 0.4,
                 outline_width: int = 2):
        self.images_dir = Path(images_dir)
        self.labels_dir = Path(labels_dir)
        self.output_dir = Path(output_dir)
        self.fill_color = fill_color
        self.alpha = alpha
        self.outline_width = outline_width
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _hex_to_rgb(self, hex_color: str) -> tuple:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _load_label(self, label_file: Path) -> list:
        """Load YOLO format polygon labels from TXT file."""
        polygons = []
        if not label_file.exists():
            return polygons
            
        with open(label_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or '|' in line:
                    continue
                    
                parts = line.split()
                class_id = int(parts[0])
                coords = [float(x) for x in parts[1:]]
                
                if len(coords) >= 8 and len(coords) % 2 == 0:
                    polygons.append({
                        'class': class_id,
                        'coords': coords
                    })
                    
        return polygons
    
    def _denormalize_coords(self, normalized_coords: list, img_width: int, img_height: int) -> list:
        """Convert normalized coordinates (0-1) to pixel coordinates."""
        return [
            normalized_coords[i] * (img_width if i % 2 == 0 else img_height)
            for i in range(len(normalized_coords))
        ]
    
    def _draw_overlay(self, image: Image.Image, polygons: list) -> Image.Image:
        """Draw green polygon overlay on image."""
        overlay = image.copy().convert("RGBA")
        draw = ImageDraw.Draw(overlay)
        
        img_width, img_height = image.size
        fill_rgba = (*self._hex_to_rgb(self.fill_color), int(255 * self.alpha))
        
        for polygon_data in polygons:
            normalized_coords = polygon_data['coords']
            pixel_coords = self._denormalize_coords(normalized_coords, img_width, img_height)
            
            polygon_points = [
                (int(pixel_coords[i]), int(pixel_coords[i+1]))
                for i in range(0, len(pixel_coords), 2)
            ]
            
            draw.polygon(polygon_points, fill=fill_rgba, outline=self.fill_color, width=self.outline_width)
        
        result = Image.alpha_composite(image.convert("RGBA"), overlay)
        return result.convert("RGB")
    
    def process_dataset(self):
        """Process all images iteratively."""
        image_files = list(self.images_dir.glob("*.png")) + list(self.images_dir.glob("*.jpg"))
        
        logger.info(f"Found {len(image_files)} images to process")
        
        processed_count = 0
        skipped_count = 0
        
        for img_path in image_files:
            label_path = self.labels_dir / f"{img_path.stem}.txt"
            output_path = self.output_dir / img_path.name
            
            # Skip if output already exists (crash recovery)
            if output_path.exists():
                logger.info(f"Skipping {img_path.name} (already processed)")
                continue
            
            if not label_path.exists():
                logger.warning(f"Label file not found for {img_path.name}, skipping")
                skipped_count += 1
                continue
            
            try:
                logger.info(f"Processing: {img_path.name}")
                
                image = Image.open(img_path)
                polygons = self._load_label(label_path)
                
                if not polygons:
                    logger.warning(f"No polygons found in {label_path.name}, skipping")
                    skipped_count += 1
                    image.close()
                    continue
                
                visualized_image = self._draw_overlay(image, polygons)
                
                visualized_image.save(output_path, "PNG")
                
                image.close()
                visualized_image.close()
                
                processed_count += 1
                logger.info(f"Saved: {output_path.name}")
                
            except Exception as e:
                logger.error(f"Error processing {img_path.name}: {e}")
                skipped_count += 1
        
        logger.info(f"Processing complete!")
        logger.info(f"Successfully processed: {processed_count} images")
        logger.info(f"Skipped: {skipped_count} images")
        logger.info(f"Output saved to: {self.output_dir}")


def main():
    base_dir = Path(__file__).parent.parent
    
    images_dir = base_dir / "dataset" / "dataset-for-viz" / "images"
    labels_dir = base_dir / "dataset" / "dataset-for-viz" / "labels"
    output_dir = base_dir / "dataset" / "dataset-for-viz" / "visualized"
    
    visualizer = DatasetVisualizer(
        images_dir=str(images_dir),
        labels_dir=str(labels_dir),
        output_dir=str(output_dir),
        fill_color="#22c55e",
        alpha=0.4,
        outline_width=2
    )
    
    visualizer.process_dataset()


if __name__ == "__main__":
    main()
from PIL import Image, ImageDraw
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class MaskGenerator:
    def __init__(self, fill_color: str = "#FF0000", alpha: float = 0.4):
        self.fill_color = fill_color
        self.alpha = alpha

    def generate_mask(
        self, image: Image.Image, detections: List[Dict[str, Any]]
    ) -> Image.Image:
        """Generate mask overlay with filled polygons."""
        mask = image.copy().convert("RGBA")
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        for det in detections:
            fill = (*self._hex_to_rgb(self.fill_color), int(255 * self.alpha))
            
            if "polygon" in det:
                # OBB Polygon: [x1, y1, x2, y2, x3, y3, x4, y4]
                # Convert flattened list to list of tuples [(x1,y1), (x2,y2), ...]
                points = det["polygon"]
                polygon_coords = list(zip(points[0::2], points[1::2]))
                draw.polygon(polygon_coords, fill=fill, outline=self.fill_color)
            else:
                # Standard BBox
                bbox = det["bbox"]
                x1, y1, x2, y2 = bbox
                draw.rectangle([x1, y1, x2, y2], fill=fill, outline=self.fill_color)

        mask = Image.alpha_composite(mask, overlay)
        return mask.convert("RGB")

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

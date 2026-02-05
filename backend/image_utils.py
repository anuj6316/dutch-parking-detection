import base64
import io
from PIL import Image
from typing import List

def decode_image(base64_string: str) -> Image.Image:
    """Decode base64 string to PIL Image."""
    if "," in base64_string:
        header, data = base64_string.split(",", 1)
    else:
        data = base64_string
    img_data = base64.b64decode(data)
    return Image.open(io.BytesIO(img_data))

def encode_image(image: Image.Image, format: str = "JPEG", quality: int = 85) -> str:
    """Encode PIL Image to base64 string."""
    buffer = io.BytesIO()
    image.save(buffer, format=format, quality=quality)
    b64_data = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/{format.lower()};base64,{b64_data}"

def crop_from_bbox(image: Image.Image, bbox: List[float]) -> Image.Image:
    """Crop image using [x1, y1, x2, y2] bounding box."""
    x1, y1, x2, y2 = [float(b) for b in bbox]
    return image.crop((x1, y1, x2, y2))

def bbox_to_obb(bbox: List[float]) -> List[float]:
    """Convert [x1, y1, x2, y2] to [x1, y1, x2, y1, x2, y2, x1, y2]."""
    x1, y1, x2, y2 = [float(b) for b in bbox]
    return [x1, y1, x2, y1, x2, y2, x1, y2]

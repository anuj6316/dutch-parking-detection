"""
Utility functions for cropping OBB (Oriented Bounding Box) regions from images.
Uses perspective transform for accurate, rotation-corrected crops.
"""

import cv2
import numpy as np
from PIL import Image
from typing import List, Tuple


def crop_obb_region(
    image: Image.Image,
    obb_coords: List[float]
) -> Image.Image:
    """
    Crop an oriented bounding box (OBB) region from an image
    using a perspective transform.

    Args:
        image: PIL Image
        obb_coords: [x1, y1, x2, y2, x3, y3, x4, y4] (clockwise or counter-clockwise)

    Returns:
        Cropped PIL Image containing only the OBB region (perspective-corrected)
    """

    # Convert PIL → NumPy (RGB)
    img = np.array(image)
    h, w = img.shape[:2]

    # OBB points
    pts = np.array(obb_coords, dtype=np.float32).reshape(4, 2)

    # Ensure consistent point order: top-left, top-right, bottom-right, bottom-left
    def order_points(pts):
        rect = np.zeros((4, 2), dtype=np.float32)
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)

        rect[0] = pts[np.argmin(s)]      # top-left
        rect[2] = pts[np.argmax(s)]      # bottom-right
        rect[1] = pts[np.argmin(diff)]   # top-right
        rect[3] = pts[np.argmax(diff)]   # bottom-left
        return rect

    rect = order_points(pts)

    # Compute width and height of the cropped image
    width = int(max(
        np.linalg.norm(rect[0] - rect[1]),
        np.linalg.norm(rect[2] - rect[3])
    ))
    height = int(max(
        np.linalg.norm(rect[0] - rect[3]),
        np.linalg.norm(rect[1] - rect[2])
    ))

    if width <= 0 or height <= 0:
        raise ValueError("Invalid OBB dimensions")

    # Destination points
    dst = np.array([
        [0, 0],
        [width - 1, 0],
        [width - 1, height - 1],
        [0, height - 1]
    ], dtype=np.float32)

    # Perspective transform
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(img, M, (width, height))

    return Image.fromarray(warped)


def get_crop_bounds(
    obb_coords: List[float],
    image_width: int,
    image_height: int,
    padding: int = 10
) -> Tuple[int, int, int, int]:
    """
    Get the axis-aligned bounding box for an OBB region (legacy support).
    """
    x_coords = [obb_coords[i] for i in range(0, 8, 2)]
    y_coords = [obb_coords[i] for i in range(1, 8, 2)]
    
    min_x = max(0, int(min(x_coords)) - padding)
    min_y = max(0, int(min(y_coords)) - padding)
    max_x = min(image_width, int(max(x_coords)) + padding)
    max_y = min(image_height, int(max(y_coords)) + padding)
    
    return (min_x, min_y, max_x, max_y)

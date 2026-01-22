"""
Parking Capacity Estimator

Calculates the approximate number of vehicles that can fit in a detected parking space
based on the OBB (Oriented Bounding Box) area.
"""

import math
from typing import Dict, Any, List, Tuple
import numpy as np


# Standard parking spot dimensions (in meters)
STANDARD_PARKING_SPOT = {
    "length": 5.0,  # meters (typical car length ~4.5m + buffer)
    "width": 2.5,   # meters (typical car width ~1.8m + door opening space)
    "area": 12.5    # square meters
}

# Compact parking spot dimensions
COMPACT_PARKING_SPOT = {
    "length": 4.5,
    "width": 2.3,
    "area": 10.35
}

# Resolution: 5cm per pixel for PDOK imagery
METERS_PER_PIXEL = 0.05


def calculate_obb_area_pixels(obb_coords: List[float]) -> float:
    """
    Calculate the area of an Oriented Bounding Box or polygon in square pixels.
    Uses the Shoelace formula for polygon area.
    
    Args:
        obb_coords: [x1, y1, x2, y2, x3, y3, x4, y4, ...] polygon coordinates
                   Can be 4 points (8 coords) for OBB or more for merged polygons
        
    Returns:
        Area in square pixels
    """
    if len(obb_coords) < 6:  # Need at least 3 points (6 coordinates)
        return 0.0
    
    # Extract x and y coordinates
    x = [obb_coords[i] for i in range(0, len(obb_coords), 2)]
    y = [obb_coords[i] for i in range(1, len(obb_coords), 2)]
    
    # Shoelace formula
    n = len(x)
    if n < 3:
        return 0.0
    
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += x[i] * y[j]
        area -= x[j] * y[i]
    
    return abs(area) / 2.0


def calculate_obb_dimensions_pixels(obb_coords: List[float]) -> Tuple[float, float]:
    """
    Calculate the width and height of an OBB or polygon in pixels.
    For merged polygons, calculates bounding box dimensions.
    
    Args:
        obb_coords: [x1, y1, x2, y2, x3, y3, x4, y4, ...] polygon coordinates
        
    Returns:
        (width, height) tuple in pixels (bounding box dimensions)
    """
    if len(obb_coords) < 6:  # Need at least 3 points
        return (0.0, 0.0)
    
    # Extract all x and y coordinates
    x_coords = [obb_coords[i] for i in range(0, len(obb_coords), 2)]
    y_coords = [obb_coords[i] for i in range(1, len(obb_coords), 2)]
    
    # Calculate bounding box dimensions
    width = max(x_coords) - min(x_coords)
    height = max(y_coords) - min(y_coords)
    
    return (width, height)


def estimate_parking_capacity(
    obb_coords: List[float],
    meters_per_pixel: float = METERS_PER_PIXEL,
    spot_type: str = "standard"
) -> Dict[str, Any]:
    """
    Estimate how many vehicles can fit in the parking space.
    
    Args:
        obb_coords: [x1, y1, x2, y2, x3, y3, x4, y4] OBB corners in pixels
        meters_per_pixel: Image resolution (default: 0.05m = 5cm for PDOK)
        spot_type: "standard" or "compact"
        
    Returns:
        {
            "area_sq_meters": float,
            "dimensions_meters": (width, height),
            "estimated_capacity": int,
            "capacity_range": (min, max),
            "spot_type": str
        }
    """
    # Get parking spot dimensions
    spot = STANDARD_PARKING_SPOT if spot_type == "standard" else COMPACT_PARKING_SPOT
    
    # Calculate area in pixels
    area_pixels = calculate_obb_area_pixels(obb_coords)
    
    # Convert to square meters
    area_sq_meters = area_pixels * (meters_per_pixel ** 2)
    
    # Calculate dimensions in pixels and convert to meters
    width_px, height_px = calculate_obb_dimensions_pixels(obb_coords)
    width_m = width_px * meters_per_pixel
    height_m = height_px * meters_per_pixel
    
    # Estimate capacity based on area
    # Account for ~70-85% efficiency (aisles, turning space, etc.)
    efficiency_low = 0.65
    efficiency_high = 0.85
    
    capacity_low = int(area_sq_meters * efficiency_low / spot["area"])
    capacity_high = int(area_sq_meters * efficiency_high / spot["area"])
    
    # Best estimate using average efficiency
    estimated_capacity = int(area_sq_meters * 0.75 / spot["area"])
    
    # Also calculate based on linear arrangement
    # How many cars can fit along the length?
    cars_along_length = int(width_m / spot["width"])
    cars_along_width = int(height_m / spot["width"])
    
    # For a parking lot, typically cars are parked perpendicular to aisles
    # This gives a rough linear estimate
    linear_estimate = max(cars_along_length, cars_along_width)
    
    return {
        "area_sq_meters": round(area_sq_meters, 2),
        "dimensions_meters": (round(width_m, 2), round(height_m, 2)),
        "estimated_capacity": max(1, estimated_capacity),
        "capacity_range": (max(0, capacity_low), max(1, capacity_high)),
        "linear_estimate": linear_estimate,
        "spot_type": spot_type,
        "spot_size_sq_m": spot["area"]
    }


def estimate_capacity_from_dimensions(
    width_px: int,
    height_px: int,
    meters_per_pixel: float = METERS_PER_PIXEL,
    spot_type: str = "standard"
) -> Dict[str, Any]:
    """
    Estimate capacity based on image dimensions (e.g. from a cropped image).
    
    Args:
        width_px: Image width in pixels
        height_px: Image height in pixels
        meters_per_pixel: Resolution
        spot_type: "standard" or "compact"
        
    Returns:
        Capacity info dict
    """
    # Get parking spot dimensions
    spot = STANDARD_PARKING_SPOT if spot_type == "standard" else COMPACT_PARKING_SPOT
    
    # Calculate area
    area_pixels = width_px * height_px
    area_sq_meters = area_pixels * (meters_per_pixel ** 2)
    
    # Dimensions in meters
    width_m = width_px * meters_per_pixel
    height_m = height_px * meters_per_pixel
    
    # Estimate capacity (using same efficiency logic as estimate_parking_capacity)
    efficiency_low = 0.65
    efficiency_high = 0.85
    
    capacity_low = int(area_sq_meters * efficiency_low / spot["area"])
    capacity_high = int(area_sq_meters * efficiency_high / spot["area"])
    
    # Best estimate
    estimated_capacity = int(area_sq_meters * 0.75 / spot["area"])
    
    return {
        "area_sq_meters": round(area_sq_meters, 2),
        "dimensions_meters": (round(width_m, 2), round(height_m, 2)),
        "estimated_capacity": max(1, estimated_capacity),
        "capacity_range": (max(0, capacity_low), max(1, capacity_high)),
        "spot_type": spot_type,
        "spot_size_sq_m": spot["area"]
    }


def calculate_occupancy_stats(
    total_capacity: int,
    vehicle_count: int
) -> Dict[str, Any]:
    """
    Calculate occupancy statistics for a parking area.
    
    Args:
        total_capacity: Estimated total parking capacity
        vehicle_count: Number of vehicles detected
        
    Returns:
        Occupancy statistics dictionary
    """
    if total_capacity <= 0:
        return {
            "occupancy_rate": 0,
            "available_spots": 0,
            "occupied_spots": vehicle_count,
            "status": "unknown"
        }
    
    occupancy_rate = min(100, (vehicle_count / total_capacity) * 100)
    available_spots = max(0, total_capacity - vehicle_count)
    
    # Determine status
    if occupancy_rate >= 90:
        status = "full"
    elif occupancy_rate >= 70:
        status = "busy"
    elif occupancy_rate >= 30:
        status = "moderate"
    else:
        status = "available"
    
    return {
        "occupancy_rate": round(occupancy_rate, 1),
        "available_spots": available_spots,
        "occupied_spots": vehicle_count,
        "total_capacity": total_capacity,
        "status": status
    }


# Test function
if __name__ == "__main__":
    # Test with sample OBB coordinates
    # Simulating a ~50x20 meter parking area at 5cm resolution
    # That's 1000x400 pixels
    test_obb = [
        0, 0,      # top-left
        1000, 0,   # top-right
        1000, 400, # bottom-right
        0, 400     # bottom-left
    ]
    
    result = estimate_parking_capacity(test_obb)
    print(f"Parking Space Analysis:")
    print(f"  Area: {result['area_sq_meters']} m²")
    print(f"  Dimensions: {result['dimensions_meters'][0]}m x {result['dimensions_meters'][1]}m")
    print(f"  Estimated Capacity: {result['estimated_capacity']} vehicles")
    print(f"  Capacity Range: {result['capacity_range'][0]} - {result['capacity_range'][1]}")
    
    # Test occupancy stats
    stats = calculate_occupancy_stats(result['estimated_capacity'], 8)
    print(f"\nOccupancy Stats (with 8 vehicles):")
    print(f"  Occupancy Rate: {stats['occupancy_rate']}%")
    print(f"  Available Spots: {stats['available_spots']}")
    print(f"  Status: {stats['status']}")

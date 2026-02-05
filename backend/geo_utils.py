import math
from typing import Dict, Tuple, List

def deg2num(lat_deg: float, lon_deg: float, zoom: int) -> Tuple[int, int]:
    """
    Converts Latitude and Longitude into Tile Coordinates (X, Y).
    This is based on the Slippy Map Tilenames math.
    """
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def num2deg(xtile: float, ytile: float, zoom: int) -> Tuple[float, float]:
    """
    Converts Tile Coordinates (X, Y) back to Latitude and Longitude (Top-Left corner).
    Supports float tile coordinates for sub-tile precision.
    """
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

def pixel_to_geo(
    x: float, y: float, width: int, height: int, bounds: Dict[str, float]
) -> Tuple[float, float]:
    """
    Convert pixel coordinates to (lat, lng) using Mercator projection math.
    """
    def lat_to_merc(lat):
        return math.log(math.tan(math.radians(lat) / 2 + math.pi / 4))

    def merc_to_lat(merc):
        return math.degrees(2 * math.atan(math.exp(merc)) - math.pi / 2)

    min_lat = bounds["minLat"]
    max_lat = bounds["maxLat"]
    min_lng = bounds["minLng"]
    max_lng = bounds["maxLng"]

    # Longitude is linear
    lng = min_lng + (x / width) * (max_lng - min_lng)

    # Latitude is non-linear (Mercator)
    merc_max = lat_to_merc(max_lat)
    merc_min = lat_to_merc(min_lat)

    # Invert: y=0 is top (merc_max), y=height is bottom (merc_min)
    merc_y = merc_max - (y / height) * (merc_max - merc_min)
    lat = merc_to_lat(merc_y)

    return lat, lng

def get_tile_bounds(x: int, y: int, zoom: int) -> Dict[str, float]:
    """Get the geographic bounds of a specific tile."""
    # Top-Left
    tl_lat, tl_lng = num2deg(x, y, zoom)
    # Bottom-Right (top-left of the next tile)
    br_lat, br_lng = num2deg(x + 1, y + 1, zoom)
    
    return {
        "minLat": br_lat,
        "maxLat": tl_lat,
        "minLng": tl_lng,
        "maxLng": br_lng
    }

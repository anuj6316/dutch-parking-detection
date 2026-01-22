import math
import requests
from PIL import Image
from io import BytesIO
import concurrent.futures

# Configuration based on your training script
CONFIG = {
    "zoom_level": 21,
    "stitch_tiles": 6,  # 6x6 grid
    "tile_size": 256,
    "final_size": 1536, # 6 * 256
    "timeout": 15,
    "retry_attempts": 3,
}

def deg2num(lat_deg, lon_deg, zoom):
    """
    Converts Latitude and Longitude into Tile Coordinates (X, Y).
    This is based on the Slippy Map Tilenames math.
    """
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def num2deg(xtile, ytile, zoom):
    """
    Converts Tile Coordinates (X, Y) back to Latitude and Longitude (Top-Left corner).
    """
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

def get_grid_bounds(lat, lng):
    """
    Returns the geographic bounds (minLat, minLng, maxLat, maxLng) of our 6x6 grid.
    """
    center_x, center_y = deg2num(lat, lng, CONFIG["zoom_level"])
    grid_size = CONFIG["stitch_tiles"]
    offset = grid_size // 2
    
    # Top-Left tile corners
    tl_lat, tl_lng = num2deg(center_x - offset, center_y - offset, CONFIG["zoom_level"])
    # Bottom-Right tile corners (we need the bottom-right corner of the tile, so we take top-left of the next one)
    br_lat, br_lng = num2deg(center_x + offset, center_y + offset, CONFIG["zoom_level"])
    
    # Since Latitude decreases as we go down (Y increases), tl_lat is maxLat and br_lat is minLat
    return {
        "minLat": br_lat,
        "maxLat": tl_lat,
        "minLng": tl_lng,
        "maxLng": br_lng
    }

def fetch_single_tile(x, y, zoom):
    """
    Fetches a single 256x256 satellite tile from Google.
    """
    url = f"https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={zoom}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for attempt in range(CONFIG["retry_attempts"]):
        try:
            response = requests.get(url, headers=headers, timeout=CONFIG["timeout"])
            if response.status_code == 200:
                return Image.open(BytesIO(response.content))
        except Exception:
            continue
    return None

def get_high_res_image(lat, lng):
    """
    The main function that:
    1. Finds the center tile for your coordinates.
    2. Fetches a 6x6 grid of surrounding tiles.
    3. Stitches them together into one big 1536x1536 image.
    """
    center_x, center_y = deg2num(lat, lng, CONFIG["zoom_level"])
    grid_size = CONFIG["stitch_tiles"]
    offset = grid_size // 2
    tile_size = CONFIG["tile_size"]
    
    # Create a blank canvas for our 6x6 grid
    stitched = Image.new('RGB', (grid_size * tile_size, grid_size * tile_size))
    
    # We use ThreadPoolExecutor to fetch multiple tiles at the same time (much faster!)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_tile = {}
        for dy in range(grid_size):
            for dx in range(grid_size):
                x = center_x + dx - offset
                y = center_y + dy - offset
                future = executor.submit(fetch_single_tile, x, y, CONFIG["zoom_level"])
                future_to_tile[future] = (dx, dy)
        
        for future in concurrent.futures.as_completed(future_to_tile):
            dx, dy = future_to_tile[future]
            tile = future.result()
            if tile:
                stitched.paste(tile, (dx * tile_size, dy * tile_size))
    
    return stitched


/**
 * Utility functions for Geographic calculations and tile URL generation.
 * Handles Google Satellite tile fetching at Zoom 21.
 */

export const ZOOM_LEVEL = 21;
export const TILE_SIZE = 256;
export const MERGED_SIZE = 1536;
export const SOURCE_TILES_PER_MERGED = 6;

// Added 20% overlap: Stride is 80% of the block size (6 tiles * 0.8 = 4.8)
export const CENTER_STRIDE_TILES = 4.8;

// Fixed: Added missing grid dimension constants for 3x3 (9 tiles) default configuration
export const CENTER_GRID_COLS = 3;
export const CENTER_GRID_ROWS = 3;

// Approximate meters per tile at Zoom 21 in the Netherlands (Lat ~52)
// Earth circumference ~40,075,000m. 2^21 tiles at Z21. 
// At equator: ~19m. At Lat 52: 19 * cos(52) ~ 11.7m.
export const METERS_PER_TILE = 11.7; 

// This now represents the STRIDE distance in meters to ensure the grid covers the area with overlap
export const METERS_PER_MERGED_BLOCK = METERS_PER_TILE * CENTER_STRIDE_TILES; // ~56.16m (Stride with 20% overlap)

export interface TileGridInfo {
    tiles: TileInfo[];
    centerTile: { x: number; y: number };
}

export interface TileInfo {
    tileIndex: number;
    x: number;
    y: number;
    bounds: {
        minLat: number;
        maxLat: number;
        minLng: number;
        maxLng: number;
    };
    url: string;
}

export interface MergedCenter {
    index: number;
    lat: number;
    lng: number;
    centerTileX: number;
    centerTileY: number;
    bounds: {
        minLat: number;
        maxLat: number;
        minLng: number;
        maxLng: number;
    };
}

/**
 * Calculates distance in meters between two lat/lng points.
 */
export function getDistanceMeters(lat1: number, lon1: number, lat2: number, lon2: number) {
    const R = 6371e3; // metres
    const φ1 = lat1 * Math.PI / 180;
    const φ2 = lat2 * Math.PI / 180;
    const Δφ = (lat2 - lat1) * Math.PI / 180;
    const Δλ = (lon2 - lon1) * Math.PI / 180;

    const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
        Math.cos(φ1) * Math.cos(φ2) *
        Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c;
}

/**
 * Converts Latitude and Longitude into Tile Coordinates (X, Y).
 */
export function latLngToTileXY(lat: number, lng: number, zoom: number): { x: number; y: number } {
    const latRad = lat * (Math.PI / 180);
    const n = 2.0 ** zoom;
    const x = Math.floor((lng + 180.0) / 360.0 * n);
    const y = Math.floor((1.0 - Math.asinh(Math.tan(latRad)) / Math.PI) / 2.0 * n);
    return { x, y };
}

/**
 * Converts Tile Coordinates (X, Y) back to Latitude and Longitude.
 */
export function tileXYToLatLng(x: number, y: number, zoom: number): { lat: number; lng: number } {
    const n = 2.0 ** zoom;
    const lng = x / n * 360.0 - 180.0;
    const latRad = Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n)));
    const lat = latRad * (180.0 / Math.PI);
    return { lat, lng };
}

/**
 * Gets the bounding box for a specific tile.
 */
export function getTileBounds(x: number, y: number, zoom: number): {
    minLat: number;
    maxLat: number;
    minLng: number;
    maxLng: number;
} {
    const n = 2.0 ** zoom;
    const minLng = x / n * 360.0 - 180.0;
    const maxLng = (x + 1) / n * 360.0 - 180.0;
    const latRad = Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n)));
    const maxLat = latRad * (180.0 / Math.PI);
    const latRad2 = Math.atan(Math.sinh(Math.PI * (1 - 2 * (y + 1) / n)));
    const minLat = latRad2 * (180.0 / Math.PI);
    return { minLat, maxLat, minLng, maxLng };
}

export function getGoogleSatelliteTileUrl(x: number, y: number, zoom: number = ZOOM_LEVEL): string {
    return `https://mt1.google.com/vt/lyrs=s&x=${x}&y=${y}&z=${zoom}`;
}

export function getPDOKTileUrl(x: number, y: number, zoom: number = ZOOM_LEVEL): string {
    // Zoom 21 is not available on PDOK, max is usually 19 or 20 for high res
    // But for consistency we use the same math.
    return `https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0/Actueel_orthoHR/EPSG:3857/${zoom}/${x}/${y}.jpeg`;
}

export function getTileUrl(x: number, y: number, zoom: number = ZOOM_LEVEL, source: 'google' | 'pdok' = 'pdok'): string {
    if (source === 'pdok') return getPDOKTileUrl(x, y, zoom);
    return getGoogleSatelliteTileUrl(x, y, zoom);
}

export function calculateTileGrid(
    centerLat: number,
    centerLng: number,
    gridCols: number,
    gridRows: number,
    zoom: number = ZOOM_LEVEL
): TileGridInfo {
    const { x: cx, y: cy } = latLngToTileXY(centerLat, centerLng, zoom);
    const offsetX = Math.floor(gridCols / 2);
    const offsetY = Math.floor(gridRows / 2);

    const tiles: TileInfo[] = [];

    for (let dy = 0; dy < gridRows; dy++) {
        for (let dx = 0; dx < gridCols; dx++) {
            const x = cx + dx - offsetX;
            const y = cy + dy - offsetY;
            const bounds = getTileBounds(x, y, zoom);
            tiles.push({
                tileIndex: dy * gridCols + dx,
                x,
                y,
                bounds,
                url: getGoogleSatelliteTileUrl(x, y, zoom)
            });
        }
    }

    return { tiles, centerTile: { x: cx, y: cy } };
}

export function calculateCenterGrid(
    centerLat: number,
    centerLng: number,
    cols: number,
    rows: number,
    strideTiles: number = CENTER_STRIDE_TILES,
    zoom: number = ZOOM_LEVEL
): MergedCenter[] {
    const centers: MergedCenter[] = [];
    const offsetX = Math.floor(cols / 2);
    const offsetY = Math.floor(rows / 2);
    const { x: mainCenterTileX, y: mainCenterTileY } = latLngToTileXY(centerLat, centerLng, zoom);

    for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
            // Using floating point tileX/Y allows for sub-tile precision in block centering
            const tileX = mainCenterTileX + (col - offsetX) * strideTiles;
            const tileY = mainCenterTileY + (row - offsetY) * strideTiles;
            const { lat, lng } = tileXYToLatLng(tileX, tileY, zoom);

            // We alignment the bounds calculation with integer tile grids for image fetching
            const bounds = getMergedTileBounds(Math.round(tileX), Math.round(tileY), zoom);

            centers.push({
                index: row * cols + col,
                lat,
                lng,
                centerTileX: Math.round(tileX),
                centerTileY: Math.round(tileY),
                bounds
            });
        }
    }

    return centers;
}

export function getMergedTileBounds(
    centerTileX: number,
    centerTileY: number,
    zoom: number = ZOOM_LEVEL
): { minLat: number; maxLat: number; minLng: number; maxLng: number } {
    const tileCount = SOURCE_TILES_PER_MERGED;
    const offset = Math.floor(tileCount / 2);

    const minTileX = centerTileX - offset;
    const maxTileX = minTileX + tileCount;
    const minTileY = centerTileY - offset;
    const maxTileY = minTileY + tileCount;

    const minLat = tileXYToLatLng(minTileX, maxTileY, zoom).lat;
    const maxLat = tileXYToLatLng(minTileX, minTileY, zoom).lat;
    const minLng = tileXYToLatLng(minTileX, minTileY, zoom).lng;
    const maxLng = tileXYToLatLng(maxTileX, minTileY, zoom).lng;

    return { minLat, maxLat, minLng, maxLng };
}

/**
 * Calculates the total number of processing blocks (1536x1536) needed to cover a municipality GeoJSON.
 */
export function calculateMunicipalityCoverage(geojson: any) {
    if (!geojson) return null;

    let coords: number[][] = [];
    if (geojson.type === 'Polygon') {
        coords = geojson.coordinates[0];
    } else if (geojson.type === 'MultiPolygon') {
        geojson.coordinates.forEach((poly: any) => {
            if (poly && poly[0]) {
                poly[0].forEach((pt: number[]) => coords.push(pt));
            }
        });
    }

    if (coords.length === 0) return null;

    // 1. Find the absolute Bounding Box of all polygon points
    let minLat = coords[0][1], maxLat = coords[0][1];
    let minLng = coords[0][0], maxLng = coords[0][0];

    coords.forEach(pt => {
        const [lng, lat] = pt;
        minLat = Math.min(minLat, lat);
        maxLat = Math.max(maxLat, lat);
        minLng = Math.min(minLng, lng);
        maxLng = Math.max(maxLng, lng);
    });

    // 2. Calculate dimensions in meters
    const widthMeters = getDistanceMeters(minLat, minLng, minLat, maxLng);
    const heightMeters = getDistanceMeters(minLat, minLng, maxLat, minLng);

    // 3. Calculate Grid Coverage (Bounding Box)
    // We use the STRIDE (56.16m) to calculate how many blocks would cover this rectangle
    const cols = Math.ceil(widthMeters / METERS_PER_MERGED_BLOCK);
    const rows = Math.ceil(heightMeters / METERS_PER_MERGED_BLOCK);
    const totalBlocks = cols * rows;

    // 4. Calculate Approximate Area (km2)
    const areaSqKm = (widthMeters * heightMeters) / 1000000;

    return {
        cols,
        rows,
        totalBlocks,
        widthKm: widthMeters / 1000,
        heightKm: heightMeters / 1000,
        areaSqKm,
        bounds: { minLat, maxLat, minLng, maxLng }
    };
}

/**
 * Extracts latitude and longitude from a Google Maps URL or coordinate string.
 * Supports:
 * - https://www.google.com/maps/@lat,lng,zoomz
 * - https://www.google.com/maps/search/?api=1&query=lat,lng
 * - https://www.google.com/maps/place/Name/@lat,lng,zoomz
 * - Bare coordinates: "52.1538, 5.3725"
 */
export function parseLocationInput(input: string): { lat: number; lng: number } | null {
    if (!input || typeof input !== 'string') return null;
    
    const trimmedInput = input.trim();
    console.log("[GeoUtils] Parsing location input:", trimmedInput);

    try {
        // 1. Check for @lat,lng format
        const atMatch = trimmedInput.match(/@(-?\d+\.\d+),(-?\d+\.\d+)/);
        if (atMatch) {
            return { lat: parseFloat(atMatch[1]), lng: parseFloat(atMatch[2]) };
        }

        // 2. Check for query=lat,lng or q=lat,lng
        const queryMatch = trimmedInput.match(/[?&](?:query|q)=(-?\d+\.\d+),(-?\d+\.\d+)/);
        if (queryMatch) {
            return { lat: parseFloat(queryMatch[1]), lng: parseFloat(queryMatch[2]) };
        }

        // 3. Check for coordinates in path segments (e.g., .../dir/52.15,5.37/...)
        const pathMatch = trimmedInput.match(/\/maps\/(?:dir|search|place|[\w+]+)\/(-?\d+\.\d+),(-?\d+\.\d+)/);
        if (pathMatch) {
            return { lat: parseFloat(pathMatch[1]), lng: parseFloat(pathMatch[2]) };
        }

        // 4. Check for bare coordinates "lat, lng"
        const bareMatch = trimmedInput.match(/^(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)$/);
        if (bareMatch) {
            return { lat: parseFloat(bareMatch[1]), lng: parseFloat(bareMatch[2]) };
        }

        // 5. Last resort: search for any "lat,lng" pair in the string
        const generalMatch = trimmedInput.match(/(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)/);
        if (generalMatch) {
            const lat = parseFloat(generalMatch[1]);
            const lng = parseFloat(generalMatch[2]);
            if (lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
                return { lat, lng };
            }
        }

        return null;
    } catch (e) {
        console.error("[GeoUtils] Error parsing input for coordinates:", e);
        return null;
    }
}

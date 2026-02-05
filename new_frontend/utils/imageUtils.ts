import {
    ZOOM_LEVEL,
    TILE_SIZE,
    CENTER_GRID_COLS,
    CENTER_GRID_ROWS,
    MERGED_SIZE,
    SOURCE_TILES_PER_MERGED,
    calculateCenterGrid,
    calculateTileGrid,
    getGoogleSatelliteTileUrl,
    getPDOKTileUrl,
    getTileUrl,
    MergedCenter
} from './geoUtils';
import { TileBounds, TileConfig, MergedTileFetchResult } from '../types';

const TIMEOUT_MS = 15000;

export async function fetchGoogleSatelliteTile(
    url: string,
    timeoutMs: number = TIMEOUT_MS
): Promise<HTMLImageElement | null> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
        // We use fetch here which requires CORS support from the server
        const response = await fetch(url, { signal: controller.signal });
        clearTimeout(timeoutId);

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const blob = await response.blob();
        const objectUrl = URL.createObjectURL(blob);

        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = "Anonymous";
            img.onload = () => resolve(img);
            img.onerror = () => {
                URL.revokeObjectURL(objectUrl);
                reject(new Error(`Failed to load image data`));
            };
            img.src = objectUrl;
        });
    } catch (error) {
        console.warn(`Tile load failed (${url}):`, error);
        return null;
    }
}

function createPlaceholderTile(): string {
    const canvas = document.createElement('canvas');
    canvas.width = TILE_SIZE;
    canvas.height = TILE_SIZE;
    const ctx = canvas.getContext('2d');
    if (ctx) {
        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, TILE_SIZE, TILE_SIZE);
        ctx.fillStyle = '#ffffff';
        ctx.font = '24px sans-serif';
        ctx.fillText('Tile Unavailable', 20, 50);
    }
    return canvas.toDataURL('image/jpeg', 0.75);
}

/**
 * Fetches a single 6×6 tile grid and merges into a 1536×1536 image.
 */
async function fetchAndMerge6x6Grid(centerLat: number, centerLng: number): Promise<{
    mergedUrl: string;
    bounds: TileBounds;
    centerInfo: MergedCenter;
}> {
    // Use the default high-res ZOOM_LEVEL (21) as primary
    const { tiles, centerTile } = calculateTileGrid(centerLat, centerLng, SOURCE_TILES_PER_MERGED, SOURCE_TILES_PER_MERGED, ZOOM_LEVEL);

    const images: (HTMLImageElement | null)[] = [];
    
    // Sequential fetch with sleep to avoid rate limits
    for (const tile of tiles) {
        let img: HTMLImageElement | null = null;
        
        // 1. Try Google (Primary)
        try {
            const googleUrl = getGoogleSatelliteTileUrl(tile.x, tile.y, ZOOM_LEVEL);
            img = await fetchGoogleSatelliteTile(googleUrl, TIMEOUT_MS);
        } catch (e) {
            // Ignore, try fallback
        }

        // 2. Fallback to PDOK if Google failed
        if (!img) {
            try {
                // Note: PDOK at Z21 might not be available or might be upscaled, but we try it as fallback
                const pdokUrl = getPDOKTileUrl(tile.x, tile.y, ZOOM_LEVEL);
                img = await fetchGoogleSatelliteTile(pdokUrl, TIMEOUT_MS);
            } catch (e) {
                console.warn(`Tile ${tile.x},${tile.y} failed both Google and PDOK`);
            }
        }

        images.push(img);
        
        // Sleep 100ms between tiles
        await new Promise(resolve => setTimeout(resolve, 100));
    }

    const mergedCanvas = document.createElement('canvas');
    mergedCanvas.width = MERGED_SIZE;
    mergedCanvas.height = MERGED_SIZE;
    const ctx = mergedCanvas.getContext('2d');

    if (ctx) {
        images.forEach((img, index) => {
            if (img) {
                const col = index % SOURCE_TILES_PER_MERGED;
                const row = Math.floor(index / SOURCE_TILES_PER_MERGED);
                ctx.drawImage(img, col * TILE_SIZE, row * TILE_SIZE);
            }
        });
    }

    const bounds = getGoogleSatelliteTileBounds(centerTile.x, centerTile.y, ZOOM_LEVEL);
    const centerInfo = calculateCenterGrid(centerLat, centerLng, 1, 1, 4.8, ZOOM_LEVEL)[0];

    return {
        mergedUrl: mergedCanvas.toDataURL('image/jpeg', 0.9),
        bounds,
        centerInfo
    };
}

function getGoogleSatelliteTileBounds(
    centerTileX: number,
    centerTileY: number,
    zoom: number = ZOOM_LEVEL
): TileBounds {
    const tileCount = SOURCE_TILES_PER_MERGED;
    const offset = Math.floor(tileCount / 2);

    const minTileX = centerTileX - offset;
    const maxTileX = minTileX + tileCount;
    const minTileY = centerTileY - offset;
    const maxTileY = minTileY + tileCount;

    function tileXYToLatLng(x: number, y: number): { lat: number; lng: number } {
        const n = 2.0 ** zoom;
        const lng = x / n * 360.0 - 180.0;
        const latRad = Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n)));
        const lat = latRad * (180.0 / Math.PI);
        return { lat, lng };
    }

    const minLat = tileXYToLatLng(minTileX, maxTileY).lat;
    const maxLat = tileXYToLatLng(minTileX, minTileY).lat;
    const minLng = tileXYToLatLng(minTileX, minTileY).lng;
    const maxLng = tileXYToLatLng(maxTileX, minTileY).lng;

    return { minLat, maxLat, minLng, maxLng };
}

/**
 * Fetches 9 center points, each with a 6×6 tile grid merged into 1536×1536.
 * Returns 9 merged images with their bounds.
 */
export async function fetch9CenterGrids(
    centerLat: number,
    centerLng: number,
    cols: number = CENTER_GRID_COLS,
    rows: number = CENTER_GRID_ROWS
): Promise<MergedTileFetchResult> {
    const centers = calculateCenterGrid(centerLat, centerLng, cols, rows);

    const mergedResults = await Promise.all(
        centers.map(async (centerInfo) => {
            try {
                const result = await fetchAndMerge6x6Grid(centerInfo.lat, centerInfo.lng);
                return {
                    ...result,
                    index: centerInfo.index
                };
            } catch (error) {
                console.warn(`Failed to fetch center ${centerInfo.index}:`, error);
                return null;
            }
        })
    );

    const validResults = mergedResults.filter((r): r is NonNullable<typeof r> => r !== null);
    const failedIndices = centers
        .map(c => c.index)
        .filter(idx => !validResults.find(r => r.index === idx));

    const tiles: string[] = [];
    const bounds: TileBounds[] = [];
    const tileConfigs: TileConfig[] = [];
    const centersInfo: MergedCenter[] = [];

    validResults.forEach(result => {
        tiles.push(result.mergedUrl);
        bounds.push(result.bounds);
        centersInfo.push(result.centerInfo);
        tileConfigs.push({
            url: '',
            x: result.index % cols,
            y: Math.floor(result.index / cols),
            bounds: result.bounds,
            tileIndex: result.index
        });
    });

    return {
        tiles,
        bounds,
        tileConfigs,
        centersInfo,
        failedIndices
    };
}

/**
 * Legacy function - fetches 3×3 grid of tiles (single merged image).
 */
export async function fetchGoogleSatelliteTiles(
    centerLat: number,
    centerLng: number,
    gridCols: number = 3,
    gridRows: number = 3,
    timeoutMs: number = TIMEOUT_MS
): Promise<{ tiles: string[], bounds: TileBounds[], tileConfigs: TileConfig[] }> {
    const { tiles: tileInfos } = calculateTileGrid(centerLat, centerLng, gridCols, gridRows);

    const images: (HTMLImageElement | null)[] = await Promise.all(
        tileInfos.map(tile => fetchGoogleSatelliteTile(tile.url, timeoutMs))
    );

    const validTiles: string[] = [];
    const validBounds: TileBounds[] = [];
    const validConfigs: TileConfig[] = [];

    images.forEach((img, index) => {
        if (img) {
            const canvas = document.createElement('canvas');
            canvas.width = TILE_SIZE;
            canvas.height = TILE_SIZE;
            const ctx = canvas.getContext('2d');
            if (ctx) {
                ctx.drawImage(img, 0, 0);
                validTiles.push(canvas.toDataURL('image/jpeg', 0.85));
            }
        } else {
            console.warn(`Tile ${index} failed to load, using placeholder`);
            validTiles.push(createPlaceholderTile());
        }
        validBounds.push(tileInfos[index].bounds);
        validConfigs.push({
            url: tileInfos[index].url,
            x: tileInfos[index].x,
            y: tileInfos[index].y,
            bounds: tileInfos[index].bounds,
            tileIndex: tileInfos[index].tileIndex
        });
    });

    return { tiles: validTiles, bounds: validBounds, tileConfigs: validConfigs };
}

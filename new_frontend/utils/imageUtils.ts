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
    const { tiles, centerTile } = calculateTileGrid(centerLat, centerLng, SOURCE_TILES_PER_MERGED, SOURCE_TILES_PER_MERGED);

    const images: (HTMLImageElement | null)[] = await Promise.all(
        tiles.map(tile => fetchGoogleSatelliteTile(tile.url, TIMEOUT_MS))
    );

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

    const bounds = getGoogleSatelliteTileBounds(centerTile.x, centerTile.y);
    const centerInfo = calculateCenterGrid(centerLat, centerLng, 1, 1)[0];

    return {
        mergedUrl: mergedCanvas.toDataURL('image/jpeg', 0.9),
        bounds,
        centerInfo
    };
}

function getGoogleSatelliteTileBounds(
    centerTileX: number,
    centerTileY: number
): TileBounds {
    const tileCount = SOURCE_TILES_PER_MERGED;
    const offset = Math.floor(tileCount / 2);

    const minTileX = centerTileX - offset;
    const maxTileX = minTileX + tileCount;
    const minTileY = centerTileY - offset;
    const maxTileY = minTileY + tileCount;

    function tileXYToLatLng(x: number, y: number): { lat: number; lng: number } {
        const n = 2.0 ** ZOOM_LEVEL;
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

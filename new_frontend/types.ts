/**
 * Represents a single detected parking space.
 */
export interface Space {
    id: string;
    status: 'Occupied' | 'Empty';
    confidence: number;

    vehicleCount?: number;
    croppedImage?: string;
    croppedOverlay?: string;

    boundingBox?: number[];
    localBoundingBox?: number[];

    tileIndex?: number;

    geoBoundingBox?: [number, number, number, number];
    geoPolygon?: [number, number][];
    geoObbCorners?: [number, number][];
    googleMapsLink?: string;

    vlmVerified?: boolean | null;
    vlmReason?: string;

    areaSqMeters?: number;
    estimatedCapacity?: number;
    dimensionsMeters?: [number, number];
}

/**
 * Aggregated metrics for a detection job.
 */
export interface JobMetrics {
    occupancyRate: number;
    occupancyRateChange: number;
    totalSpaces: number;
    occupiedCount: number;
    emptyCount: number;

    totalEstimatedCapacity?: number;
    totalVehiclesDetected?: number;

    availableSpots?: number;
    occupancyStatus?: string;
    totalAreaSqMeters?: number;
}

/**
 * Grounding source reference (from Google Search/Maps).
 */
export interface GroundingChunk {
    web?: { uri?: string; title?: string };
    maps?: { uri?: string; title?: string; };
}

/**
 * Contextual location information retrieved via grounding.
 */
export interface LocationInfo {
    summary: string;
    chunks: GroundingChunk[];
}

/**
 * Geographic bounds for a tile.
 */
export interface TileBounds {
    minLat: number;
    maxLat: number;
    minLng: number;
    maxLng: number;
}

/**
 * Configuration for a specific image tile within the grid.
 */
export interface TileConfig {
    url: string;
    x: number;
    y: number;
    bounds: TileBounds;
    tileIndex: number;
}

/**
 * Payload for each tile sent to the backend.
 */
export interface TilePayload {
    image_base64: string;
    tile_index: number;
    bounds: TileBounds;
}

/**
 * Request body for the analyze-tiles endpoint.
 */
export interface TileAnalysisRequest {
    tiles: TilePayload[];
    confidence_threshold: number;
    count_vehicles: boolean;
}

/**
 * Response from the analyze-tiles endpoint.
 */
export interface TileAnalysisResponse {
    detections: DetectionResult[];
    total_spaces: number;
    total_vehicles_detected: number;
    total_estimated_capacity: number;
    per_tile_stats: Record<string, { spaces: number; vehicles: number }>;
    failed_tiles: number[];
    logs?: string[];
    detection_masks?: Array<{ tile_index: number; mask: string }>;
}

/**
 * Enhanced response from the modular pipeline.
 */
export interface PipelineResponse {
    detections: DetectionResult[];
    detection_masks: Array<{ tile_index: number; mask: string }>;
    total_spaces: number;
    total_vehicles_detected: number;
    total_estimated_capacity: number;
    per_tile_stats: Record<string, { spaces: number; vehicles: number }>;
    failed_tiles: number[];
    logs: string[];
}

/**
 * Individual detection result from the backend.
 */
export interface DetectionResult {
    obb_coordinates: number[];
    tile_index: number;
    confidence: number[];
    vehicle_count: number;
    is_occupied: boolean;
    geoBoundingBox: [number, number, number, number];
    geoPolygon: [number, number][];
    geo_obb_corners?: [number, number][];
    google_maps_link?: string;
    area_sq_meters: number;
    estimated_capacity: number;
    cropped_image?: string;
    cropped_overlay?: string;
    dimensions_meters?: [number, number];
}

/**
 * Result from fetching Google Satellite tiles.
 */
export interface TileFetchResult {
    tiles: string[];
    bounds: TileBounds[];
    tileConfigs: TileConfig[];
}

/**
 * Result from fetching 9 center grids with merged images.
 */
export interface MergedTileFetchResult {
    tiles: string[];
    bounds: TileBounds[];
    tileConfigs: TileConfig[];
    centersInfo: Array<{
        index: number;
        lat: number;
        lng: number;
        centerTileX: number;
        centerTileY: number;
        bounds: TileBounds;
    }>;
    failedIndices: number[];
}

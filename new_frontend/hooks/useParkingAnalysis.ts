import { useState, useCallback } from 'react';
import { Space, JobMetrics, LocationInfo, DetectionResult } from '../types';
import { ProcessingStep } from '../components/ProcessingStatus';
import { fetch9CenterGrids } from '../utils/imageUtils';
import { CENTER_GRID_COLS, CENTER_GRID_ROWS } from '../utils/geoUtils';
import { API_ENDPOINTS } from '../src/api/config';
import { saveAllMergedImages } from '../utils/fileUtils';

interface UseParkingAnalysisProps {
    apiKey: string | undefined;
}

export const useParkingAnalysis = ({ apiKey }: UseParkingAnalysisProps) => {
    const [status, setStatus] = useState<ProcessingStep>('idle');
    const [statusDetails, setStatusDetails] = useState<string>("");

    const [spaces, setSpaces] = useState<Space[]>([]);
    const [metrics, setMetrics] = useState<JobMetrics>({
        occupancyRate: 0, occupancyRateChange: 0, totalSpaces: 0, occupiedCount: 0, emptyCount: 0
    });
    const [locationInfo, setLocationInfo] = useState<LocationInfo | null>(null);
    const [detectionConfidence, setDetectionConfidence] = useState<number>(0.25);

    const [tileConfigs, setTileConfigs] = useState<any[]>([]);
    const [tileImages, setTileImages] = useState<string[]>([]);
    const [detectionMasks, setDetectionMasks] = useState<Array<{ tile_index: number; mask: string }>>([]);
    const [logs, setLogs] = useState<string[]>([]);

    const resetAnalysis = useCallback(() => {
        setStatus('idle');
        setStatusDetails("");
        setSpaces([]);
        setMetrics({ occupancyRate: 0, occupancyRateChange: 0, totalSpaces: 0, occupiedCount: 0, emptyCount: 0 });
        setLocationInfo(null);
        setTileConfigs([]);
        setTileImages([]);
        setDetectionMasks([]);
        setLogs([]);
    }, []);

    const runAnalysis = useCallback(async (
        center: { lat: number; lng: number },
        gridCols: number = CENTER_GRID_COLS,
        gridRows: number = CENTER_GRID_ROWS,
        municipality: string = 'unknown'
    ) => {
        const totalTiles = gridCols * gridRows;
        setStatus('analyzing');
        setLogs([]);
        console.log(`[Analysis] Starting analysis at ${center.lat}, ${center.lng}`);
        setStatusDetails(`Fetching ${totalTiles} center grids (6×6 tiles each)...`);

        try {
            console.log(`[Analysis] Fetching ${totalTiles} center grids...`);
            const fetchResult = await fetch9CenterGrids(center.lat, center.lng, gridCols, gridRows);

            if (fetchResult.tiles.length === 0) {
                throw new Error("No tiles could be loaded from any center");
            }

            const fetchPercent = Math.round((fetchResult.tiles.length / totalTiles) * 100);
            console.log(`[Analysis] Fetched ${fetchResult.tiles.length}/${totalTiles} merged images (${fetchPercent}%)`);
            setLogs(prev => [...prev, `[Step 1/5] Generated ${fetchResult.tiles.length} merged images`]);
            setTileImages(fetchResult.tiles);
            setTileConfigs(fetchResult.tileConfigs);

            const saveResult = await saveAllMergedImages(fetchResult.tiles, municipality);
            if (saveResult.success) {
                console.log(`[Analysis] Saved merged images to local directory`);
            } else {
                console.warn(`[Analysis] Failed to save merged images: ${saveResult.error}`);
            }

            const fetchStatus = fetchResult.failedIndices.length > 0
                ? `Loaded ${fetchResult.tiles.length}/${totalTiles} merged images (${fetchPercent}%). Processing...`
                : `Loaded ${fetchResult.tiles.length}/${totalTiles} merged images. Processing sequentially...`;
            console.log(`[Analysis] ${fetchStatus}`);
            setStatusDetails(fetchStatus);

            console.log(`[Analysis] Sending ${fetchResult.tiles.length} merged images to API...`);
            setLogs(prev => [...prev, `[Step 2/5] YOLO detection started`]);
            setStatusDetails(`Processing: 0%`);

            const response = await fetch(API_ENDPOINTS.ANALYZE_TILES, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tiles: fetchResult.tiles.map((tileData, index) => ({
                        image_base64: tileData,
                        tile_index: index,
                        bounds: fetchResult.bounds[index]
                    })),
                    confidence_threshold: detectionConfidence,
                    count_vehicles: true
                })
            });

            if (!response.ok) {
                throw new Error(`Analysis failed: ${response.status}`);
            }

            const analysisResult = await response.json();
            console.log(`[Analysis] API returned ${analysisResult.detections.length} detections`);

            // Add logs from backend response
            if (analysisResult.logs && Array.isArray(analysisResult.logs)) {
                setLogs(prev => [...prev, ...analysisResult.logs]);
            }

            // Store detection masks for debugging
            if (analysisResult.detection_masks && Array.isArray(analysisResult.detection_masks)) {
                setDetectionMasks(analysisResult.detection_masks);
            }

            setStatusDetails(`Processing: 100%`);

            const allSpaces: Space[] = analysisResult.detections.map((det: DetectionResult, idx: number) => {
                const tileBounds = fetchResult.bounds[det.tile_index] || fetchResult.bounds[0];

                // Validate geoPolygon
                let geoPolygon = det.geoPolygon;
                if (geoPolygon && Array.isArray(geoPolygon)) {
                    // Ensure polygon is closed for Leaflet (first point = last point)
                    if (geoPolygon.length > 0) {
                        const first = geoPolygon[0];
                        const last = geoPolygon[geoPolygon.length - 1];
                        if (first && last && (first[0] !== last[0] || first[1] !== last[1])) {
                            geoPolygon = [...geoPolygon, [first[0], first[1]]];
                        }
                    }
                    
                    // Log merged polygons for debugging
                    if (geoPolygon.length > 5) {
                        console.log(`[Frontend] Merged polygon detected: ${geoPolygon.length} points for SPOT-${idx + 1}`);
                    }
                }

                return {
                    id: `SPOT-${idx + 1}`,
                    status: det.is_occupied ? 'Occupied' : 'Empty',
                    confidence: Math.round(det.confidence[0] * 100),
                    vehicleCount: det.vehicle_count,
                    croppedImage: det.cropped_image,
                    croppedOverlay: det.cropped_overlay,
                    boundingBox: null,
                    tileIndex: det.tile_index,
                    localBoundingBox: null,
                    geoBoundingBox: det.geoBoundingBox,
                    geoPolygon: geoPolygon,
                    areaSqMeters: det.area_sq_meters,
                    estimatedCapacity: det.estimated_capacity,
                    dimensionsMeters: det.dimensions_meters
                };
            });

            setSpaces(allSpaces);

            const occupiedCount = allSpaces.filter(s => s.status === 'Occupied').length;
            const totalVehicles = allSpaces.reduce((sum, s) => sum + (s.vehicleCount || 0), 0);
            const totalCapacity = allSpaces.reduce((sum, s) => sum + (s.estimatedCapacity || 1), 0);
            const occupancyRate = totalCapacity > 0
                ? Math.round((totalVehicles / totalCapacity) * 100)
                : 0;

            let statusMessage = `Analysis complete: ${analysisResult.total_spaces} spaces, ${analysisResult.total_vehicles_detected} vehicles`;
            if (analysisResult.failed_tiles && analysisResult.failed_tiles.length > 0) {
                statusMessage += `. ${analysisResult.failed_tiles.length} tiles failed.`;
            }

            console.log(`[Analysis] ${statusMessage}`);
            setLogs(prev => [...prev, `[Pipeline] Complete: ${analysisResult.total_spaces} total detections`]);

            setMetrics({
                occupancyRate,
                occupancyRateChange: 0,
                totalSpaces: analysisResult.total_spaces,
                occupiedCount,
                emptyCount: analysisResult.total_spaces - occupiedCount,
                totalEstimatedCapacity: analysisResult.total_estimated_capacity,
                totalVehiclesDetected: analysisResult.total_vehicles_detected,
                availableSpots: analysisResult.total_estimated_capacity - analysisResult.total_vehicles_detected,
                occupancyStatus: occupancyRate >= 90 ? 'full' : occupancyRate >= 70 ? 'busy' : occupancyRate >= 30 ? 'moderate' : 'available'
            });

            setStatusDetails(statusMessage);
            setStatus('completed');

        } catch (error: any) {
            console.error("[Analysis] Error:", error);
            setLogs(prev => [...prev, `[Error] ${error.message}`]);
            setStatusDetails(`Error: ${error.message}`);
            setStatus('idle');
        }
    }, [apiKey, detectionConfidence]);

    return {
        status,
        statusDetails,
        spaces,
        metrics,
        locationInfo,
        tileImages,
        tileConfigs,
        detectionMasks,
        logs,
        detectionConfidence,
        setDetectionConfidence,
        resetAnalysis,
        runAnalysis
    };
};
import { useState, useCallback } from 'react';
import { Space, JobMetrics, LocationInfo, DetectionResult } from '../types';
import { ProcessingStep } from '../components/ProcessingStatus';
import { fetch9CenterGrids } from '../utils/imageUtils';
import { CENTER_GRID_COLS, CENTER_GRID_ROWS } from '../utils/geoUtils';
import { API_ENDPOINTS, SAVE_IMAGES_ENABLED } from '../src/api/config';
import { saveAllMergedImages } from '../utils/fileUtils';

interface UseParkingAnalysisProps {
    apiKey: string | undefined;
}

export const useParkingAnalysis = ({ apiKey }: UseParkingAnalysisProps) => {
    const [status, setStatus] = useState<ProcessingStep>('idle');
    const [statusDetails, setStatusDetails] = useState<string>("");
    const [progress, setProgress] = useState<number>(0);

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
        setProgress(0);
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

            if (SAVE_IMAGES_ENABLED) {
                const saveResult = await saveAllMergedImages(fetchResult.tiles, 'unified');
                if (saveResult.success) {
                    console.log(`[Analysis] Saved merged images to unified pool`);
                } else {
                    console.warn(`[Analysis] Failed to save merged images: ${saveResult.error}`);
                }
            } else {
                console.log(`[Analysis] Image logging is disabled (SAVE_IMAGES_ENABLED=false)`);
            }

            const fetchStatus = fetchResult.failedIndices.length > 0
                ? `Loaded ${fetchResult.tiles.length}/${totalTiles} merged images (${fetchPercent}%). Processing...`
                : `Loaded ${fetchResult.tiles.length}/${totalTiles} merged images. Processing sequentially...`;
            console.log(`[Analysis] ${fetchStatus}`);
            setStatusDetails(fetchStatus);

            console.log(`[Analysis] Sending ${fetchResult.tiles.length} merged images to API (Streaming)...`);
            setLogs(prev => [...prev, `[Step 2/5] YOLO detection started`]);
            setStatusDetails(`Processing: 0%`);

            const response = await fetch(API_ENDPOINTS.ANALYZE_TILES_STREAM, {
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

            if (!response.ok) throw new Error(`Analysis failed: ${response.status}`);

            // --- STREAM PROCESSING ---
            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            if (reader) {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || ''; // Keep the last partial line

                    for (const line of lines) {
                        if (!line.trim()) continue;
                        try {
                            const update = JSON.parse(line);
                            
                            if (update.type === 'log') {
                                setLogs(prev => [...prev, update.message]);
                            } else if (update.type === 'progress') {
                                setProgress(update.value);
                                setStatusDetails(`Processing: ${update.value}%`);
                            } else if (update.type === 'final_result') {
                                const result = update.data;
                                console.log(`[Analysis] Received final result: ${result.detections.length} detections`);
                                
                                if (result.detection_masks) {
                                    setDetectionMasks(result.detection_masks);
                                }

                                const allSpaces: Space[] = result.detections.map((det: DetectionResult, idx: number) => {
                                    let geoPolygon = det.geoPolygon;
                                    if (geoPolygon && Array.isArray(geoPolygon) && geoPolygon.length > 0) {
                                        const first = geoPolygon[0];
                                        const last = geoPolygon[geoPolygon.length - 1];
                                        if (first && last && (first[0] !== last[0] || first[1] !== last[1])) {
                                            geoPolygon = [...geoPolygon, [first[0], first[1]]];
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
                                const occupancyRate = totalCapacity > 0 ? Math.round((totalVehicles / totalCapacity) * 100) : 0;

                                setMetrics({
                                    occupancyRate,
                                    occupancyRateChange: 0,
                                    totalSpaces: result.total_spaces,
                                    occupiedCount,
                                    emptyCount: result.total_spaces - occupiedCount,
                                    totalEstimatedCapacity: result.total_spaces, // Fallback
                                    totalVehiclesDetected: totalVehicles,
                                    availableSpots: result.total_spaces - occupiedCount,
                                    occupancyStatus: occupancyRate >= 90 ? 'full' : occupancyRate >= 70 ? 'busy' : occupancyRate >= 30 ? 'moderate' : 'available'
                                });

                                setStatusDetails(`Analysis complete: ${result.total_spaces} spaces, ${totalVehicles} vehicles`);
                                setStatus('completed');
                            }
                        } catch (e) {
                            console.error("Error parsing stream line:", e, line);
                        }
                    }
                }
            }
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
        progress,
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
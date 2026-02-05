import { useState, useCallback, useRef } from 'react';
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

    // Refs for cancellation
    const abortControllerRef = useRef<AbortController | null>(null);
    const currentJobIdRef = useRef<string | null>(null);
    const logWsRef = useRef<WebSocket | null>(null);

    const isTerminatingRef = useRef<boolean>(false);

    const terminateAnalysis = useCallback(async () => {
        const jobId = currentJobIdRef.current;
        if (!jobId || isTerminatingRef.current) return;
        
        isTerminatingRef.current = true;
        console.log(`[Analysis] Terminating Job: ${jobId}`);
        
        // 1. Abort HTTP Request
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
        }

        // 2. Signal Backend
        try {
            await fetch(`${API_ENDPOINTS.CANCEL_ANALYSIS}${jobId}`, { method: 'POST' });
        } catch (e) {
            console.warn("Backend cancellation failed:", e);
        }

        // 3. Cleanup WebSocket
        if (logWsRef.current) {
            logWsRef.current.close();
            logWsRef.current = null;
        }

        setLogs(prev => [...prev, "🛑 Analysis terminated by user."]);
        setStatusDetails("Analysis terminated.");
        setStatus('idle');
        setProgress(0);
        currentJobIdRef.current = null;
        isTerminatingRef.current = false;
    }, []);

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

            // Telemetry Separation: 
            const jobId = `job-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
            currentJobIdRef.current = jobId;
            console.log(`[Analysis] Initializing Job: ${jobId}`);
            
            // Step 2: Connect to Log WebSocket
            const ws = new WebSocket(`${API_ENDPOINTS.ANALYZE_LOGS_WS}${jobId}`);
            logWsRef.current = ws;
            
            ws.onopen = () => {
                console.log("[WS] Log stream connected");
                setLogs(prev => [...prev, "[System] Log stream connected. Waiting for analysis..."]);
            };

            ws.onmessage = (event) => {
                try {
                    const update = JSON.parse(event.data);
                    if (update.type === 'log') {
                        setLogs(prev => [...prev, update.message]);
                    } else if (update.type === 'progress') {
                        setProgress(update.value);
                        setStatusDetails(`Processing: ${update.value}%`);
                    } else if (update.type === 'error') {
                        setLogs(prev => [...prev, `[Error] ${update.message}`]);
                    }
                } catch (e) {
                    console.error("Error parsing log message:", e);
                }
            };

            // Step 3: HTTP Request with AbortController
            abortControllerRef.current = new AbortController();
            
            const payload = {
                tiles: fetchResult.tiles.map((tileData, index) => ({
                    image_base64: tileData,
                    tile_index: index,
                    bounds: fetchResult.bounds[index]
                })),
                confidence_threshold: detectionConfidence,
                count_vehicles: true,
                job_id: jobId
            };

            // We use fetch/axios for the heavy lifting now
            const response = await fetch(API_ENDPOINTS.ANALYZE_TILES, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                signal: abortControllerRef.current.signal
            });

            if (!response.ok) {
                if (response.status === 499) return; // Ignore intentional cancellation
                throw new Error(`Analysis failed: ${response.statusText}`);
            }

            const result = await response.json();
            
            // Handle Final Result (same as before)
            console.log(`[Analysis] Received final result via HTTP`);
            
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
            if (logWsRef.current) logWsRef.current.close();
            currentJobIdRef.current = null;

        } catch (error: any) {
            if (error.name === 'AbortError') {
                console.log("[Analysis] Request aborted successfully");
                return;
            }
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
        terminateAnalysis,
        runAnalysis
    };
};
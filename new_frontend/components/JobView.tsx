
import React, { useState, useEffect, useMemo } from 'react';
import JobHeader, { Area } from './JobHeader';
import ProcessingStatus from './ProcessingStatus';
import StatsCards from './StatsCards';
import MapSection from './MapSection';
import SidebarInfo from './SidebarInfo';
import SpacesTable from './SpacesTable';
import AreaSelectorMap from './AreaSelectorMap';
import { useParkingAnalysis } from '../hooks/useParkingAnalysis';
import { getDistanceMeters, METERS_PER_MERGED_BLOCK, calculateMunicipalityCoverage } from '../utils/geoUtils';
import municipalitiesList from '../data/dutch_municipalities.json';

const PREDEFINED_AREAS: Area[] = [
    { id: 'amersfoort', name: 'Amersfoort Station', bbox: '52.1538,5.3725' },
    { id: 'utrecht', name: 'Utrecht P+R Westraven', bbox: '52.0620,5.1060' },
    { id: 'amsterdam', name: 'Amsterdam Arena P1', bbox: '52.3120,4.9410' },
    { id: 'rotterdam', name: 'Rotterdam Kralingse Zoom', bbox: '51.9170,4.5210' },
    { id: 'eindhoven', name: 'Eindhoven High Tech Campus', bbox: '51.4170,5.4610' },
];

// Merge predefined areas with municipalities
const ALL_AREAS: Area[] = [
    ...PREDEFINED_AREAS,
    ...municipalitiesList.map(m => ({
        id: m.toLowerCase().replace(/[^a-z0-9]/g, '-'),
        name: m,
        bbox: '' // Will be fetched on demand
    })).filter(m => !PREDEFINED_AREAS.some(p => p.id === m.id)) // Only dedup by exact ID match
];

interface JobViewProps {
    onBack: () => void;
}

const JobView: React.FC<JobViewProps> = ({ onBack }) => {
    const [selectedAreaId, setSelectedAreaId] = useState<string>(PREDEFINED_AREAS[0].id);
    const [activeSpaceId, setActiveSpaceId] = useState<string | null>(null);
    const [useCustomArea, setUseCustomArea] = useState(false);
    const [showAreaSelector, setShowAreaSelector] = useState(false);
    const [customBounds, setCustomBounds] = useState<{
        minLat: number; maxLat: number; minLng: number; maxLng: number
    } | null>(null);
    
    // State to hold fetched coordinates for municipalities
    const [dynamicBbox, setDynamicBbox] = useState<string | null>(null);
    const [municipalityPolygon, setMunicipalityPolygon] = useState<any | null>(null);
    const [municipalityCoverage, setMunicipalityCoverage] = useState<any | null>(null);
    const [isFetchingLocation, setIsFetchingLocation] = useState(false);
    const [totalImages, setTotalImages] = useState<number>(9);

    const selectedArea = ALL_AREAS.find(a => a.id === selectedAreaId) || PREDEFINED_AREAS[0];
    
    // Determine the active bbox: custom > dynamic (fetched) > predefined
    const effectiveBbox = dynamicBbox || selectedArea.bbox || PREDEFINED_AREAS[0].bbox;
    const [predefinedLat, predefinedLng] = effectiveBbox.split(',').map(Number);

    // Fetch coordinates/polygon when a municipality is selected
    useEffect(() => {
        const area = ALL_AREAS.find(a => a.id === selectedAreaId);
        if (!area) return;

        const fetchLocation = async () => {
            setIsFetchingLocation(true);
            setMunicipalityPolygon(null); // Reset polygon while loading
            setMunicipalityCoverage(null); // Reset coverage
            
            // Only reset dynamicBbox if we are switching to a completely new fetch
            if (area.bbox) {
                setDynamicBbox(null);
            }

            try {
                // Step 1: Search for the exact area name
                let response = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(area.name)},Netherlands&format=json&limit=1&polygon_geojson=1`);
                let data = await response.json();
                
                let foundPolygon = false;
                if (data && data.length > 0) {
                    const { lat, lon, geojson } = data[0];
                    if (!area.bbox) setDynamicBbox(`${lat},${lon}`);
                    
                    if (geojson && (geojson.type === 'Polygon' || geojson.type === 'MultiPolygon')) {
                        setMunicipalityPolygon(geojson);
                        setMunicipalityCoverage(calculateMunicipalityCoverage(geojson));
                        foundPolygon = true;
                    }
                }

                // Step 2: Fallback - If not a polygon (e.g., a Station), try to search for the city/municipality part
                if (!foundPolygon) {
                    // Extract the first word or handle common cases
                    const cityName = area.name.split(' ')[0];
                    const fallbackResponse = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(cityName)},Netherlands&format=json&limit=1&polygon_geojson=1&featuretype=settlement`);
                    const fallbackData = await fallbackResponse.json();
                    
                    if (fallbackData && fallbackData.length > 0) {
                        const { geojson } = fallbackData[0];
                        if (geojson && (geojson.type === 'Polygon' || geojson.type === 'MultiPolygon')) {
                            setMunicipalityPolygon(geojson);
                            setMunicipalityCoverage(calculateMunicipalityCoverage(geojson));
                        }
                    }
                }
            } catch (error) {
                console.error("Failed to fetch location:", error);
            } finally {
                setIsFetchingLocation(false);
            }
        };

        fetchLocation();
    }, [selectedAreaId]);

    // Scaling predefined bounds to cover ~420m x 350m (exactly 6x5 grid of 30 blocks)
    // 0.003 deg Lat is ~333m. 0.006 deg Lng is ~420m at Lat 52.
    const currentBounds = customBounds || { 
        minLat: predefinedLat - 0.0015, 
        maxLat: predefinedLat + 0.0015, 
        minLng: predefinedLng - 0.003, 
        maxLng: predefinedLng + 0.003 
    };

    const center = useCustomArea && customBounds
        ? {
            lat: (customBounds.minLat + customBounds.maxLat) / 2,
            lng: (customBounds.minLng + customBounds.maxLng) / 2
        }
        : { lat: predefinedLat, lng: predefinedLng };

    // Calculate Dynamic Grid Dimensions
    const gridDimensions = useMemo(() => {
        if (!currentBounds) return { cols: 6, rows: 5 };
        
        const widthMeters = getDistanceMeters(currentBounds.minLat, currentBounds.minLng, currentBounds.minLat, currentBounds.maxLng);
        const heightMeters = getDistanceMeters(currentBounds.minLat, currentBounds.minLng, currentBounds.maxLat, currentBounds.minLng);
        
        // Logical limits for the grid based on meters
        const cols = Math.min(10, Math.max(1, Math.ceil(widthMeters / METERS_PER_MERGED_BLOCK)));
        const rows = Math.min(10, Math.max(1, Math.ceil(heightMeters / METERS_PER_MERGED_BLOCK)));
        
        return { cols, rows };
    }, [currentBounds]);

    const {
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
    } = useParkingAnalysis({ apiKey: process.env.API_KEY });

    const isAnalyzing = status !== 'idle' && status !== 'completed';

    const maskedImagesMap = useMemo(() => {
        const map = new Map<number, string[]>();
        detectionMasks.forEach(dm => {
            map.set(dm.tile_index, [dm.mask]);
        });
        return map;
    }, [detectionMasks]);

    // Sync totalImages with calculated grid when using custom area
    useEffect(() => {
        if (useCustomArea) {
            setTotalImages(gridDimensions.cols * gridDimensions.rows);
        }
    }, [useCustomArea, gridDimensions]);

    useEffect(() => {
        resetAnalysis();
        setActiveSpaceId(null);
    }, [selectedAreaId, useCustomArea, customBounds, resetAnalysis]);

    const handleRunClick = () => {
        // If using custom area, use the calculated dimensions from the map selection
        // If using predefined point, calculate optimal grid from totalImages
        let cols, rows;
        if (useCustomArea) {
            cols = gridDimensions.cols;
            rows = gridDimensions.rows;
        } else {
            cols = Math.ceil(Math.sqrt(totalImages));
            rows = Math.ceil(totalImages / cols);
        }
        
        runAnalysis(center, cols, rows, selectedAreaId);
    };

    const handleLocateSpace = (spaceId: string) => {
        setActiveSpaceId(spaceId);
    };

    const handleToggleCustomArea = () => {
        if (!useCustomArea) {
            setShowAreaSelector(true);
        } else {
            setUseCustomArea(false);
            setCustomBounds(null);
        }
    };

    const handleAreaSelected = (bounds: { minLat: number; maxLat: number; minLng: number; maxLng: number }) => {
        setCustomBounds(bounds);
        setUseCustomArea(true);
        setShowAreaSelector(false);
    };

    const handleCancelAreaSelector = () => {
        setShowAreaSelector(false);
        if (!customBounds) {
            setUseCustomArea(false);
        }
    };

    const customAreaName = customBounds
        ? `Custom Area (${gridDimensions.cols}x${gridDimensions.rows} Tiles)`
        : undefined;

    return (
        <div className="w-full max-w-[1400px] flex flex-col gap-6">
            {showAreaSelector && (
                <AreaSelectorMap
                    onAreaSelected={handleAreaSelected}
                    onCancel={handleCancelAreaSelector}
                    initialCenter={center}
                />
            )}

            <JobHeader
                onRerun={handleRunClick}
                isAnalyzing={isAnalyzing}
                onBack={onBack}
                areas={ALL_AREAS}
                selectedAreaId={selectedAreaId}
                onAreaChange={setSelectedAreaId}
                detectionConfidence={detectionConfidence}
                setDetectionConfidence={setDetectionConfidence}
                useCustomArea={useCustomArea}
                onToggleCustomArea={handleToggleCustomArea}
                customAreaName={customAreaName}
                totalImages={totalImages}
                setTotalImages={setTotalImages}
            />

            <ProcessingStatus
                status={status}
                progress={progress}
                images={tileImages}
                maskedImages={maskedImagesMap}
                statusDetails={statusDetails}
                spaces={spaces}
                logs={logs}
            />

            <StatsCards metrics={metrics} />

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <MapSection
                    spaces={spaces}
                    center={center}
                    bounds={currentBounds}
                    activeSpaceId={activeSpaceId}
                    tileImages={tileImages}
                    tileConfigs={tileConfigs}
                    gridCols={gridDimensions.cols}
                    gridRows={gridDimensions.rows}
                    onSpaceClick={handleLocateSpace}
                    municipalityPolygon={municipalityPolygon}
                />
                <SidebarInfo 
                    locationInfo={locationInfo} 
                    totalImages={totalImages}
                    gridCols={useCustomArea ? gridDimensions.cols : Math.ceil(Math.sqrt(totalImages))}
                    gridRows={useCustomArea ? gridDimensions.rows : Math.ceil(totalImages / Math.ceil(Math.sqrt(totalImages)))}
                    municipalityCoverage={municipalityCoverage}
                    isFetchingLocation={isFetchingLocation}
                />
            </div>

            <SpacesTable
                spaces={spaces}
                onLocateSpace={handleLocateSpace}
                activeSpaceId={activeSpaceId}
            />
        </div>
    );
};

export default JobView;

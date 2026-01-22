
import React, { useState, useEffect, useMemo } from 'react';
import JobHeader, { Area } from './JobHeader';
import ProcessingStatus from './ProcessingStatus';
import StatsCards from './StatsCards';
import MapSection from './MapSection';
import SidebarInfo from './SidebarInfo';
import SpacesTable from './SpacesTable';
import AreaSelectorMap from './AreaSelectorMap';
import { useParkingAnalysis } from '../hooks/useParkingAnalysis';
import { getDistanceMeters, METERS_PER_MERGED_BLOCK } from '../utils/geoUtils';

const AREAS: Area[] = [
    { id: 'amersfoort', name: 'Amersfoort Station', bbox: '52.1538,5.3725' },
    { id: 'utrecht', name: 'Utrecht P+R Westraven', bbox: '52.0620,5.1060' },
    { id: 'amsterdam', name: 'Amsterdam Arena P1', bbox: '52.3120,4.9410' },
    { id: 'rotterdam', name: 'Rotterdam Kralingse Zoom', bbox: '51.9170,4.5210' },
    { id: 'eindhoven', name: 'Eindhoven High Tech Campus', bbox: '51.4170,5.4610' },
];

interface JobViewProps {
    onBack: () => void;
}

const JobView: React.FC<JobViewProps> = ({ onBack }) => {
    const [selectedAreaId, setSelectedAreaId] = useState<string>(AREAS[0].id);
    const [activeSpaceId, setActiveSpaceId] = useState<string | null>(null);
    const [useCustomArea, setUseCustomArea] = useState(false);
    const [showAreaSelector, setShowAreaSelector] = useState(false);
    const [customBounds, setCustomBounds] = useState<{
        minLat: number; maxLat: number; minLng: number; maxLng: number
    } | null>(null);

    const selectedArea = AREAS.find(a => a.id === selectedAreaId) || AREAS[0];
    const [predefinedLat, predefinedLng] = selectedArea.bbox.split(',').map(Number);

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

    useEffect(() => {
        resetAnalysis();
        setActiveSpaceId(null);
    }, [selectedAreaId, useCustomArea, customBounds, resetAnalysis]);

    const handleRunClick = () => {
        runAnalysis(center, gridDimensions.cols, gridDimensions.rows, selectedAreaId);
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
                areas={AREAS}
                selectedAreaId={selectedAreaId}
                onAreaChange={setSelectedAreaId}
                detectionConfidence={detectionConfidence}
                setDetectionConfidence={setDetectionConfidence}
                useCustomArea={useCustomArea}
                onToggleCustomArea={handleToggleCustomArea}
                customAreaName={customAreaName}
            />

            <ProcessingStatus
                status={status}
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
                />
                <SidebarInfo locationInfo={locationInfo} />
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

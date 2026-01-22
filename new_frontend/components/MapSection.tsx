
import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { Space, TileConfig } from '../types';
import { Crosshair, Map as MapIcon, Eye, EyeOff, Satellite, Grid3X3, ImageIcon } from 'lucide-react';

interface MapSectionProps {
    spaces: Space[];
    center: { lat: number; lng: number };
    bounds: {
        minLat: number;
        maxLat: number;
        minLng: number;
        maxLng: number;
    };
    activeSpaceId?: string | null;
    tileImages?: string[];
    tileConfigs?: TileConfig[];
    gridCols?: number;
    gridRows?: number;
    onSpaceClick?: (id: string) => void;
    municipalityPolygon?: any;
}

const MapSection: React.FC<MapSectionProps> = ({
    spaces,
    center,
    bounds,
    activeSpaceId,
    tileImages = [],
    tileConfigs = [],
    gridCols = 3,
    gridRows = 3,
    onSpaceClick,
    municipalityPolygon
}) => {
    const mapContainerRef = useRef<HTMLDivElement>(null);
    const mapInstanceRef = useRef<L.Map | null>(null);
    const markersLayerRef = useRef<L.LayerGroup | null>(null);
    const gridLayerRef = useRef<L.LayerGroup | null>(null);
    const tilesLayerRef = useRef<L.LayerGroup | null>(null);
    const maskLayerRef = useRef<L.Polygon | null>(null);
    const bgtLayerRef = useRef<L.TileLayer.WMS | null>(null);
    const boundaryLayerRef = useRef<L.GeoJSON | null>(null);

    const [baseLayer, setBaseLayer] = useState<'pdok' | 'google'>('google');
    const [showBGT, setShowBGT] = useState(false);
    const [showGrid, setShowGrid] = useState(true);
    const [showTileMosaic, setShowTileMosaic] = useState(true);
    const [useSpotlight, setUseSpotlight] = useState(true);

    // Initialize Leaflet Map
    useEffect(() => {
        if (!mapContainerRef.current) return;
        if (mapInstanceRef.current) return;

        const map = L.map(mapContainerRef.current, {
            center: [center.lat, center.lng],
            zoom: 19,
            zoomControl: false,
            attributionControl: false
        });

        L.control.zoom({ position: 'bottomright' }).addTo(map);

        mapInstanceRef.current = map;
        markersLayerRef.current = L.layerGroup().addTo(map);
        gridLayerRef.current = L.layerGroup().addTo(map);
        tilesLayerRef.current = L.layerGroup().addTo(map);

        map.fitBounds([[bounds.minLat, bounds.minLng], [bounds.maxLat, bounds.maxLng]]);

        return () => {
            map.remove();
            mapInstanceRef.current = null;
        };
    }, []);

    // Update map view when center or bounds change
    useEffect(() => {
        if (!mapInstanceRef.current) return;
        
        mapInstanceRef.current.flyTo([center.lat, center.lng], 19);
        
        // Optionally fit bounds if they change significantly, but flyTo is usually sufficient for centering
        // mapInstanceRef.current.fitBounds([[bounds.minLat, bounds.minLng], [bounds.maxLat, bounds.maxLng]]);
    }, [center.lat, center.lng]);

    // Render Municipality Polygon
    useEffect(() => {
        if (!mapInstanceRef.current) return;
        const map = mapInstanceRef.current;

        if (boundaryLayerRef.current) {
            map.removeLayer(boundaryLayerRef.current);
            boundaryLayerRef.current = null;
        }

        if (municipalityPolygon) {
            boundaryLayerRef.current = L.geoJSON(municipalityPolygon, {
                style: {
                    color: '#ffffff', // White base
                    weight: 3,
                    opacity: 1,
                    fillColor: 'transparent',
                    fillOpacity: 0,
                    dashArray: '10, 10',
                    className: 'municipality-border'
                },
                interactive: false
            }).addTo(map);

            // Add a secondary dashed line on top for the "candy cane" or dashed effect
            const secondaryLayer = L.geoJSON(municipalityPolygon, {
                style: {
                    color: '#ef4444', // Red segments
                    weight: 3,
                    opacity: 1,
                    fill: false,
                    dashArray: '10, 10',
                    dashOffset: '10',
                    className: 'municipality-border-red'
                },
                interactive: false
            }).addTo(map);
            
            // Group them to manage together easily if needed, or just track the main one for removal
            // For simplicity in this ref logic, we track the main layer. 
            // Ideally, we should group them in a LayerGroup.
            const group = L.layerGroup([boundaryLayerRef.current, secondaryLayer]).addTo(map);
            boundaryLayerRef.current = group as any; // Cast to bypass strict type for now or update type
            
            // Optionally fit bounds to the municipality polygon
            // map.fitBounds(boundaryLayerRef.current.getBounds());
        }
    }, [municipalityPolygon]);

    // Handle Base Layer Toggle
    useEffect(() => {
        if (!mapInstanceRef.current) return;
        const map = mapInstanceRef.current;

        map.eachLayer((layer) => {
            if (layer instanceof L.TileLayer && !(layer instanceof L.TileLayer.WMS)) {
                if (layer.options.attribution === 'PDOK' || layer.options.attribution === 'Google') {
                    map.removeLayer(layer);
                }
            }
        });

        if (baseLayer === 'pdok') {
            L.tileLayer('https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0/Actueel_orthoHR/EPSG:3857/{z}/{x}/{y}.jpeg', {
                minZoom: 6, maxZoom: 22, maxNativeZoom: 19, attribution: 'PDOK'
            }).addTo(map);
        } else {
            L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
                minZoom: 1, maxZoom: 22, attribution: 'Google'
            }).addTo(map);
        }
    }, [baseLayer]);

    // Render Tile Grid and AI Images Mosaic
    useEffect(() => {
        if (!mapInstanceRef.current || !gridLayerRef.current || !tilesLayerRef.current) return;
        const map = mapInstanceRef.current;
        gridLayerRef.current.clearLayers();
        tilesLayerRef.current.clearLayers();

        if (tileConfigs.length > 0) {
            tileConfigs.forEach((config, idx) => {
                const tileBounds: L.LatLngBoundsExpression = [
                    [config.bounds.minLat, config.bounds.minLng],
                    [config.bounds.maxLat, config.bounds.maxLng]
                ];

                // Render Grid Borders
                if (showGrid) {
                    const rect = L.rectangle(tileBounds, {
                        color: '#3b82f6',
                        weight: 2, // Increased weight to show overlapping boundaries
                        fill: true,
                        fillColor: '#3b82f6',
                        fillOpacity: 0.03,
                        opacity: 0.5,
                        dashArray: '4, 4'
                    });
                    
                    const label = `B-${idx+1}`;
                    rect.bindTooltip(label, { 
                        permanent: true, 
                        direction: 'center', 
                        className: 'bg-primary/20 text-primary border-0 text-[10px] font-bold pointer-events-none' 
                    });
                    
                    rect.addTo(gridLayerRef.current!);
                }

                // Render AI Tile Mosaic (Input Stream) with blend mode
                if (showTileMosaic && tileImages[idx]) {
                    L.imageOverlay(tileImages[idx], tileBounds, {
                        opacity: 0.7, // Lower opacity to see overlapping features
                        className: 'ai-tile-overlay shadow-lg mix-blend-screen'
                    }).addTo(tilesLayerRef.current!);
                }
            });
        } else {
            // Draw a simplified boundary for the whole job area
            L.rectangle([[bounds.minLat, bounds.minLng], [bounds.maxLat, bounds.maxLng]], {
                color: '#3b82f6', weight: 1, fill: false, dashArray: '5, 5', opacity: 0.3
            }).addTo(gridLayerRef.current!);
        }
    }, [tileConfigs, tileImages, showGrid, showTileMosaic, bounds]);

    // Handle BGT Layer Toggle
    useEffect(() => {
        if (!mapInstanceRef.current) return;
        const map = mapInstanceRef.current;
        if (showBGT) {
            bgtLayerRef.current = L.tileLayer.wms('https://service.pdok.nl/lv/bgt/wms/v1_0', {
                layers: 'bgt', format: 'image/png', transparent: true, version: '1.3.0', opacity: 0.5
            }).addTo(map);
        } else if (bgtLayerRef.current) {
            map.removeLayer(bgtLayerRef.current);
            bgtLayerRef.current = null;
        }
    }, [showBGT]);

    // Render Spaces and Spotlight Mask
    useEffect(() => {
        if (!mapInstanceRef.current || !markersLayerRef.current) return;
        const map = mapInstanceRef.current;
        markersLayerRef.current.clearLayers();
        if (maskLayerRef.current) { map.removeLayer(maskLayerRef.current); maskLayerRef.current = null; }

        const activeSpace = spaces.find(s => s.id === activeSpaceId);

        if (activeSpace && activeSpace.geoPolygon && useSpotlight) {
            const worldCoords: [number, number][] = [[-90, -180], [-90, 180], [90, 180], [90, -180]];
            const mask = L.polygon([worldCoords, activeSpace.geoPolygon], {
                color: 'black', weight: 0, fillColor: 'black', fillOpacity: 0.7, interactive: false
            }).addTo(map);
            maskLayerRef.current = mask;
        }

        // Draw individual spaces
        spaces.forEach(space => {
            if (!space.geoPolygon) return;
            const isActive = activeSpaceId === space.id;
            const color = space.status === 'Occupied' ? '#ef4444' : '#3fb950';

            const polygon = L.polygon(space.geoPolygon, {
                color: color,
                weight: isActive ? 3 : 1.5,
                opacity: 0.9,
                fillColor: color,
                fillOpacity: isActive ? 0.3 : 0.45,
                className: `cursor-pointer ${isActive ? 'active-space' : ''}`
            });

            polygon.on('click', (e) => {
                L.DomEvent.stopPropagation(e);
                if (onSpaceClick) onSpaceClick(space.id);
            });

            polygon.addTo(markersLayerRef.current!);

            if (isActive) {
                const polyBounds = L.polygon(space.geoPolygon).getBounds();
                map.flyTo(polyBounds.getCenter(), 21, { animate: true });
            }
        });
    }, [spaces, activeSpaceId, useSpotlight, onSpaceClick]);

    return (
        <div className="lg:col-span-2 rounded-xl bg-card border border-card-border overflow-hidden flex flex-col h-full min-h-[550px] shadow-lg relative group">
            <div className="p-4 border-b border-card-border flex flex-wrap justify-between items-center bg-card/80 backdrop-blur-md z-[1001] relative transition-all group-hover:bg-card">
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        <MapIcon size={18} className="text-primary" />
                        <h3 className="text-white font-bold text-sm tracking-tight uppercase">Analysis Map</h3>
                    </div>

                    <div className="flex items-center bg-black/40 rounded-lg p-0.5 border border-white/10">
                        <button
                            onClick={() => setBaseLayer('pdok')}
                            className={`px-3 py-1 text-[9px] rounded-md uppercase font-bold transition-all ${baseLayer === 'pdok' ? 'bg-primary text-white shadow-lg' : 'text-text-muted hover:text-white'}`}
                        >
                            PDOK
                        </button>
                        <button
                            onClick={() => setBaseLayer('google')}
                            className={`px-3 py-1 text-[9px] rounded-md uppercase font-bold transition-all ${baseLayer === 'google' ? 'bg-primary text-white shadow-lg' : 'text-text-muted hover:text-white'}`}
                        >
                            Google
                        </button>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <div className="px-2 py-1 bg-primary/20 rounded border border-primary/30 text-[8px] font-bold text-primary uppercase tracking-tighter mr-2">
                        20% Overlap On
                    </div>
                    
                    <button
                        onClick={() => setShowTileMosaic(!showTileMosaic)}
                        title="Show AI Input Mosaic"
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[9px] font-bold uppercase tracking-wider transition-all border ${showTileMosaic ? 'bg-primary/10 text-primary border-primary/30' : 'bg-white/5 text-text-muted border-white/10 hover:bg-white/10'}`}
                    >
                        <ImageIcon size={14} />
                        Tiles
                    </button>
                    
                    <button
                        onClick={() => setShowGrid(!showGrid)}
                        title="Toggle Grid Overlay"
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[9px] font-bold uppercase tracking-wider transition-all border ${showGrid ? 'bg-primary/10 text-primary border-primary/30' : 'bg-white/5 text-text-muted border-white/10 hover:bg-white/10'}`}
                    >
                        <Grid3X3 size={14} />
                        Grid
                    </button>

                    <button
                        onClick={() => setShowBGT(!showBGT)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[9px] font-bold uppercase tracking-wider transition-all border ${showBGT ? 'bg-primary/10 text-primary border-primary/30' : 'bg-white/5 text-text-muted border-white/10 hover:bg-white/10'}`}
                    >
                        {showBGT ? <Eye size={14} /> : <EyeOff size={14} />}
                        BGT
                    </button>

                    <button
                        onClick={() => setUseSpotlight(!useSpotlight)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[9px] font-bold uppercase tracking-wider transition-all border ${useSpotlight ? 'bg-primary/10 text-primary border-primary/30' : 'bg-white/5 text-text-muted border-white/10 hover:bg-white/10'}`}
                    >
                        <Satellite size={14} />
                        Focus
                    </button>
                </div>
            </div>

            <div className="relative flex-1 bg-background">
                <div ref={mapContainerRef} className="absolute inset-0 z-0" />

                {/* Legend Overlay */}
                <div className="absolute top-4 right-4 z-[1000] flex flex-col gap-2 pointer-events-none">
                    <div className="bg-black/80 backdrop-blur-md rounded-lg p-3 border border-white/10 flex flex-col gap-2">
                        <div className="flex items-center gap-2">
                            <span className="size-2 rounded-full bg-[#ef4444]"></span>
                            <span className="text-[9px] font-bold text-white uppercase tracking-wider">Occupied</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="size-2 rounded-full bg-[#3fb950]"></span>
                            <span className="text-[9px] font-bold text-white uppercase tracking-wider">Empty</span>
                        </div>
                    </div>
                </div>

                {/* Lat/Lng Indicator */}
                <div className="absolute bottom-4 left-4 z-[1000] px-3 py-2 rounded-lg bg-black/80 backdrop-blur-md border border-white/10 text-[9px] font-mono text-white flex items-center gap-3 pointer-events-none">
                    <div className="flex items-center gap-2">
                        <Crosshair size={10} className="text-primary" />
                        <span>{center.lat.toFixed(6)} N</span>
                    </div>
                    <div className="h-3 w-[1px] bg-white/10" />
                    <span>{center.lng.toFixed(6)} E</span>
                    <div className="h-3 w-[1px] bg-white/10" />
                    <span className="text-primary font-bold">Z21Mosaic</span>
                </div>
            </div>
        </div>
    );
};

export default MapSection;

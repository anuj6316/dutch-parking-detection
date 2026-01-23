
import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { MapPin, Check, X, Move, ZoomIn, ZoomOut, Link as LinkIcon } from 'lucide-react';
import { parseGoogleMapsUrl } from '../utils/geoUtils';

interface AreaSelectorMapProps {
    onAreaSelected: (bounds: { minLat: number; maxLat: number; minLng: number; maxLng: number }) => void;
    onCancel: () => void;
    initialCenter?: { lat: number; lng: number };
}

// Updated analysis area size to target exactly 30 tiles (6x5 grid)
// Each merged block is ~70m. 420/70 = 6. 350/70 = 5.
const AREA_WIDTH_METERS = 420;
const AREA_HEIGHT_METERS = 350;

const AreaSelectorMap: React.FC<AreaSelectorMapProps> = ({
    onAreaSelected,
    onCancel,
    initialCenter = { lat: 52.1538, lng: 5.3725 } // Default: Amersfoort
}) => {
    const mapContainerRef = useRef<HTMLDivElement>(null);
    const mapInstanceRef = useRef<L.Map | null>(null);
    const rectangleRef = useRef<L.Rectangle | null>(null);
    const [currentBounds, setCurrentBounds] = useState<{
        minLat: number;
        maxLat: number;
        minLng: number;
        maxLng: number;
    } | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [manualCoords, setManualCoords] = useState<{lat: string, lng: string}>({ 
        lat: initialCenter.lat.toFixed(5), 
        lng: initialCenter.lng.toFixed(5) 
    });
    const [googleMapsUrl, setGoogleMapsUrl] = useState('');
    const [locationName, setLocationName] = useState<string | null>(null);

    const fetchLocationName = async (lat: number, lng: number) => {
        try {
            const response = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`);
            const data = await response.json();
            if (data && data.address) {
                const addr = data.address;
                const name = addr.road || addr.suburb || addr.neighbourhood || addr.hamlet || "Unknown Street";
                const city = addr.city || addr.town || addr.village || addr.municipality || "";
                setLocationName(city ? `${name}, ${city}` : name);
            } else if (data && data.display_name) {
                 setLocationName(data.display_name.split(',')[0]);
            }
        } catch (error) {
            console.error("Reverse geocode failed:", error);
        }
    };

    // Calculate bounds from center point
    const calculateBoundsFromCenter = (lat: number, lng: number) => {
        // 1 Degree Lat ~= 111,132 meters
        const metersPerDegLat = 111132.92;
        // 1 Degree Lng ~= 111,412 * cos(lat) meters
        const metersPerDegLng = 111412.84 * Math.cos(lat * (Math.PI / 180));

        const deltaLat = (AREA_HEIGHT_METERS / 2) / metersPerDegLat;
        const deltaLng = (AREA_WIDTH_METERS / 2) / metersPerDegLng;

        return {
            minLat: lat - deltaLat,
            maxLat: lat + deltaLat,
            minLng: lng - deltaLng,
            maxLng: lng + deltaLng
        };
    };

    // Update rectangle position on map
    const updateRectangle = (bounds: { minLat: number; maxLat: number; minLng: number; maxLng: number }) => {
        if (rectangleRef.current) {
            rectangleRef.current.setBounds([
                [bounds.minLat, bounds.minLng],
                [bounds.maxLat, bounds.maxLng]
            ]);
        }
        setCurrentBounds(bounds);
        // Update manual inputs to reflect center
        const centerLat = (bounds.minLat + bounds.maxLat) / 2;
        const centerLng = (bounds.minLng + bounds.maxLng) / 2;
        setManualCoords({
            lat: centerLat.toFixed(5),
            lng: centerLng.toFixed(5)
        });
    };

    const handleManualInputSubmit = () => {
        const lat = parseFloat(manualCoords.lat);
        const lng = parseFloat(manualCoords.lng);
        
        if (!isNaN(lat) && !isNaN(lng)) {
            const newBounds = calculateBoundsFromCenter(lat, lng);
            updateRectangle(newBounds);
            if (mapInstanceRef.current) {
                mapInstanceRef.current.flyTo([lat, lng], 17);
            }
            fetchLocationName(lat, lng);
        }
    };

    const handleGoogleUrlSubmit = (url: string) => {
        console.log("handleGoogleUrlSubmit triggered with:", url);
        const coords = parseGoogleMapsUrl(url);
        if (coords) {
            console.log("Extracted coords:", coords);
            const newBounds = calculateBoundsFromCenter(coords.lat, coords.lng);
            updateRectangle(newBounds);
            if (mapInstanceRef.current) {
                console.log("Flying map to:", [coords.lat, coords.lng]);
                mapInstanceRef.current.flyTo([coords.lat, coords.lng], 17);
            } else {
                console.error("mapInstanceRef.current is null!");
            }
            fetchLocationName(coords.lat, coords.lng);
            setGoogleMapsUrl(''); // Clear after success
        } else {
            console.warn("Could not parse coordinates from URL");
        }
    };

    useEffect(() => {
        if (!mapContainerRef.current || mapInstanceRef.current) return;

        // Initialize map
        const map = L.map(mapContainerRef.current, {
            center: [initialCenter.lat, initialCenter.lng],
            zoom: 17,
            zoomControl: false
        });

        // Add zoom control to bottom right
        L.control.zoom({ position: 'bottomright' }).addTo(map);

        // Add Google Satellite Imagery
        L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
            minZoom: 1,
            maxZoom: 22,
            attribution: 'Google'
        }).addTo(map);

        // Calculate initial bounds centered on map
        const initialBounds = calculateBoundsFromCenter(initialCenter.lat, initialCenter.lng);

        // Create the fixed-size draggable rectangle
        const rectangle = L.rectangle(
            [[initialBounds.minLat, initialBounds.minLng], [initialBounds.maxLat, initialBounds.maxLng]],
            {
                color: '#ea2a33',
                weight: 3,
                fillColor: '#ea2a33',
                fillOpacity: 0.15,
                dashArray: '10, 5',
                className: 'analysis-rectangle'
            }
        ).addTo(map);

        rectangleRef.current = rectangle;
        setCurrentBounds(initialBounds);
        fetchLocationName(initialCenter.lat, initialCenter.lng);

        // Variables for dragging
        let dragStartLatLng: L.LatLng | null = null;
        let rectCenterAtDragStart: L.LatLng | null = null;

        // Enable dragging via mouse events on the rectangle
        rectangle.on('mousedown', (e: L.LeafletMouseEvent) => {
            L.DomEvent.stopPropagation(e);
            map.dragging.disable();
            dragStartLatLng = e.latlng;
            const bounds = rectangle.getBounds();
            rectCenterAtDragStart = bounds.getCenter();
            setIsDragging(true);

            const onMouseMove = (moveEvent: L.LeafletMouseEvent) => {
                if (!dragStartLatLng || !rectCenterAtDragStart) return;

                const deltaLat = moveEvent.latlng.lat - dragStartLatLng.lat;
                const deltaLng = moveEvent.latlng.lng - dragStartLatLng.lng;

                const newCenterLat = rectCenterAtDragStart.lat + deltaLat;
                const newCenterLng = rectCenterAtDragStart.lng + deltaLng;

                const newBounds = calculateBoundsFromCenter(newCenterLat, newCenterLng);
                updateRectangle(newBounds);
            };

            const onMouseUp = () => {
                map.dragging.enable();
                map.off('mousemove', onMouseMove);
                map.off('mouseup', onMouseUp);
                
                // Fetch location on drag end
                if (rectCenterAtDragStart && dragStartLatLng) {
                     // Need to calculate final center
                     // Actually, updateRectangle has been called with final bounds.
                     // But we don't have the final center easily available in this scope unless we recalc or read from state (which is stale in closure)
                     // Better to read from rectangle
                     const finalCenter = rectangle.getBounds().getCenter();
                     fetchLocationName(finalCenter.lat, finalCenter.lng);
                }

                dragStartLatLng = null;
                rectCenterAtDragStart = null;
                setIsDragging(false);
            };

            map.on('mousemove', onMouseMove);
            map.on('mouseup', onMouseUp);
        });

        // Double-click on map to move rectangle to that location
        map.on('dblclick', (e: L.LeafletMouseEvent) => {
            const newBounds = calculateBoundsFromCenter(e.latlng.lat, e.latlng.lng);
            updateRectangle(newBounds);
            fetchLocationName(e.latlng.lat, e.latlng.lng);

            // Optionally pan map to center on rectangle
            map.panTo(e.latlng);
        });

        mapInstanceRef.current = map;

        return () => {
            map.remove();
            mapInstanceRef.current = null;
            rectangleRef.current = null;
        };
    }, [initialCenter.lat, initialCenter.lng]);

    const handleConfirm = () => {
        if (currentBounds) {
            onAreaSelected(currentBounds);
        }
    };

    // Center rectangle on current map view
    const handleCenterOnMap = () => {
        if (mapInstanceRef.current) {
            const center = mapInstanceRef.current.getCenter();
            const newBounds = calculateBoundsFromCenter(center.lat, center.lng);
            updateRectangle(newBounds);
            fetchLocationName(center.lat, center.lng);
        }
    };

    return (
        <div className="fixed inset-0 z-[7000] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="w-full max-w-5xl h-[80vh] bg-card-dark rounded-2xl border border-white/10 overflow-hidden flex flex-col shadow-2xl">
                {/* Header */}
                <div className="p-4 border-b border-white/10 flex items-center justify-between bg-gradient-to-r from-primary/10 to-transparent">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-primary/20">
                            <MapPin className="text-primary" size={20} />
                        </div>
                        <div>
                            <h2 className="text-white font-bold text-lg">Position Analysis Area</h2>
                            <p className="text-text-muted text-sm flex items-center gap-2">
                                {locationName ? (
                                    <span className="text-white font-medium">{locationName}</span>
                                ) : (
                                    "Drag the rectangle or double-click to position"
                                )}
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="flex items-center bg-black/40 rounded-lg p-1 border border-white/10 group focus-within:border-primary/50 transition-colors">
                            <div className="pl-2 pr-1 text-text-muted">
                                <LinkIcon size={14} />
                            </div>
                            <input 
                                type="text" 
                                value={googleMapsUrl}
                                onChange={(e) => {
                                    setGoogleMapsUrl(e.target.value);
                                    // Only try to parse if it looks like a full URL or contains coordinates
                                    if (e.target.value.includes('google.com/maps') || e.target.value.includes('@')) {
                                        handleGoogleUrlSubmit(e.target.value);
                                    }
                                }}
                                onPaste={(e) => {
                                    const pastedText = e.clipboardData.getData('text');
                                    console.log("Pasted text:", pastedText);
                                    handleGoogleUrlSubmit(pastedText);
                                }}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                        handleGoogleUrlSubmit(googleMapsUrl);
                                    }
                                }}
                                placeholder="Paste Google Maps Link"
                                className="bg-transparent border-none w-48 text-xs text-white focus:ring-0 placeholder:text-text-muted/50"
                            />
                        </div>

                        <div className="flex items-center bg-black/40 rounded-lg p-1 border border-white/10">
                            <input 
                                type="text" 
                                value={manualCoords.lat}
                                onChange={(e) => setManualCoords({...manualCoords, lat: e.target.value})}
                                onKeyDown={(e) => e.key === 'Enter' && handleManualInputSubmit()}
                                placeholder="Lat"
                                className="bg-transparent border-none w-20 text-xs text-white text-center focus:ring-0"
                            />
                            <div className="w-[1px] h-4 bg-white/10"></div>
                            <input 
                                type="text" 
                                value={manualCoords.lng}
                                onChange={(e) => setManualCoords({...manualCoords, lng: e.target.value})}
                                onKeyDown={(e) => e.key === 'Enter' && handleManualInputSubmit()}
                                placeholder="Lng"
                                className="bg-transparent border-none w-20 text-xs text-white text-center focus:ring-0"
                            />
                            <button 
                                onClick={handleManualInputSubmit}
                                className="p-1.5 hover:bg-white/10 rounded-md transition-colors"
                            >
                                <Check size={12} className="text-primary" />
                            </button>
                        </div>
                        <button
                            onClick={onCancel}
                            className="p-2 rounded-lg hover:bg-white/10 transition-colors text-text-muted hover:text-white"
                        >
                            <X size={20} />
                        </button>
                    </div>
                </div>

                {/* Map Container */}
                <div className="flex-1 relative">
                    <div ref={mapContainerRef} className="absolute inset-0" />

                    {/* Instructions Overlay */}
                    <div className="absolute top-4 left-4 z-[1000] pointer-events-none">
                        <div className="bg-black/80 backdrop-blur-sm rounded-lg p-3 border border-white/20 max-w-sm">
                            <div className="flex flex-col gap-2 text-white text-sm">
                                <div className="flex items-center gap-2">
                                    <Move size={14} className="text-primary flex-shrink-0" />
                                    <span><strong>Drag</strong> the red rectangle to position</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <MapPin size={14} className="text-primary flex-shrink-0" />
                                    <span><strong>Double-click</strong> anywhere to move it there</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <ZoomIn size={14} className="text-primary flex-shrink-0" />
                                    <span><strong>Zoom</strong> to find your parking area</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Dragging indicator */}
                    {isDragging && (
                        <div className="absolute top-4 right-4 z-[1000]">
                            <div className="bg-primary text-white px-3 py-1.5 rounded-full text-sm font-medium animate-pulse">
                                Dragging...
                            </div>
                        </div>
                    )}

                    {/* Area size indicator */}
                    <div className="absolute bottom-4 left-4 z-[1000]">
                        <div className="bg-black/70 backdrop-blur-sm rounded-lg px-3 py-2 border border-white/10 text-xs text-text-muted">
                            Analysis area: <span className="text-white font-mono">{AREA_WIDTH_METERS}m × {AREA_HEIGHT_METERS}m</span>
                        </div>
                    </div>
                </div>

                {/* Footer with Actions */}
                <div className="p-4 border-t border-white/10 flex items-center justify-between bg-card-darker">
                    <div className="text-sm text-text-muted">
                        {currentBounds ? (
                            <span className="text-green-400 flex items-center gap-2">
                                <Check size={16} />
                                Center: {((currentBounds.minLat + currentBounds.maxLat) / 2).toFixed(5)}°, {((currentBounds.minLng + currentBounds.maxLng) / 2).toFixed(5)}°
                            </span>
                        ) : (
                            <span>Initializing...</span>
                        )}
                    </div>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={handleCenterOnMap}
                            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-white text-sm font-medium transition-colors"
                        >
                            <Move size={16} />
                            Center on View
                        </button>
                        <button
                            onClick={onCancel}
                            className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-white text-sm font-medium transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleConfirm}
                            disabled={!currentBounds}
                            className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-bold transition-all ${currentBounds
                                ? 'bg-primary hover:bg-primary/90 text-white shadow-lg shadow-primary/20'
                                : 'bg-white/5 text-white/40 cursor-not-allowed'
                                }`}
                        >
                            <Check size={16} />
                            Analyze This Area
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AreaSelectorMap;

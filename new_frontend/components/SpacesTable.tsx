import React from 'react';
import { Search, MapPin, Filter, ChevronDown, CheckCircle2, AlertCircle, ExternalLink, Car } from 'lucide-react';
import { Space } from '../types';

interface SpacesTableProps {
    spaces: Space[];
    onLocateSpace?: (id: string) => void;
    activeSpaceId?: string | null;
}

const SpacesTable: React.FC<SpacesTableProps> = ({ spaces, onLocateSpace, activeSpaceId }) => {
    return (
        <div className="bg-card border border-card-border rounded-xl flex flex-col shadow-sm">
            <div className="p-6 border-b border-card-border flex flex-col md:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                    <div className="size-10 bg-[#1c2128] border border-card-border rounded-lg flex items-center justify-center text-text-muted">
                        <Search size={18} />
                    </div>
                    <div>
                        <h3 className="text-white font-bold text-lg leading-tight">Detected Parking Spaces</h3>
                        <p className="text-text-muted text-[10px] uppercase tracking-widest font-bold">Individual detection results and confidence scores</p>
                    </div>
                </div>
                
                <div className="flex items-center gap-3">
                    <div className="relative">
                        <select className="bg-[#1c2128] border border-card-border rounded-md pl-9 pr-10 py-1.5 text-[10px] font-bold text-white appearance-none focus:ring-0 focus:border-primary tracking-wider uppercase">
                            <option>All Status</option>
                            <option>Empty Only</option>
                            <option>Occupied Only</option>
                        </select>
                        <Filter size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                        <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted" />
                    </div>
                    <div className="relative">
                        <input 
                            type="text" 
                            placeholder="Search ID..." 
                            className="bg-[#1c2128] border border-card-border rounded-md pl-9 pr-3 py-1.5 text-[10px] font-bold text-white placeholder-text-muted focus:ring-0 focus:border-primary w-44 uppercase tracking-wider" 
                        />
                        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                    </div>
                </div>
            </div>

            <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                    <thead className="bg-white/[0.02] text-[10px] uppercase font-bold text-text-muted tracking-[0.15em]">
                        <tr>
                            <th className="px-6 py-5 border-b border-card-border">Space ID</th>
                            <th className="px-6 py-5 border-b border-card-border text-center">Status</th>
                            <th className="px-6 py-5 border-b border-card-border text-center">Vehicles</th>
                            <th className="px-6 py-5 border-b border-card-border">Area</th>
                            <th className="px-6 py-5 border-b border-card-border">Availability</th>
                            <th className="px-6 py-5 border-b border-card-border text-center">VLM Check</th>
                            <th className="px-6 py-5 border-b border-card-border">Reason</th>
                            <th className="px-6 py-5 border-b border-card-border">Confidence</th>
                            <th className="px-6 py-5 border-b border-card-border text-right">Action</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-card-border text-[11px]">
                        {spaces.length > 0 ? spaces.map((space) => (
                            <tr key={space.id} className={`group transition-all ${activeSpaceId === space.id ? 'bg-primary/10' : 'hover:bg-white/[0.02]'}`}>
                                <td className="px-6 py-4 font-mono font-bold text-primary tracking-wider uppercase">
                                    {space.id}
                                </td>
                                <td className="px-6 py-4 text-center">
                                    <span className={`inline-block px-3 py-1 rounded-sm text-[9px] font-bold uppercase tracking-widest border ${
                                        space.status === 'Empty' 
                                        ? 'bg-success/10 text-success border-success/20' 
                                        : 'bg-primary/10 text-primary border-primary/20'
                                    }`}>
                                        {space.status}
                                    </span>
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex items-center justify-center gap-2 font-mono text-white">
                                        <Car size={14} className={space.vehicleCount && space.vehicleCount > 0 ? 'text-primary' : 'text-text-muted opacity-50'} />
                                        <span className="font-bold">{space.vehicleCount || 0}</span>
                                    </div>
                                </td>
                                <td className="px-6 py-4 text-text-muted italic">{space.areaSqMeters ? `${space.areaSqMeters} m²` : '—'}</td>
                                <td className="px-6 py-4">
                                    <div className="flex flex-col leading-tight">
                                        <span className="text-success font-bold text-[9px] uppercase tracking-wider">
                                            Available {Math.max(0, (space.estimatedCapacity || 1) - (space.vehicleCount || 0))}
                                        </span>
                                        <span className="text-text-muted text-[8px] uppercase tracking-tighter opacity-70">
                                            Cap: {space.estimatedCapacity || 1}
                                        </span>
                                    </div>
                                </td>
                                <td className="px-6 py-4 text-center">
                                    <div className="flex items-center justify-center gap-2 text-text-muted">
                                        <AlertCircle size={14} className="opacity-50" />
                                        <span className="font-bold text-[10px]">N/A</span>
                                    </div>
                                </td>
                                <td className="px-6 py-4 text-text-muted italic opacity-50">—</td>
                                <td className="px-6 py-4">
                                    <div className="flex flex-col gap-1.5 w-32">
                                        <div className="flex justify-between items-center text-[8px] font-bold uppercase tracking-widest text-text-muted">
                                            <span>AI Score</span>
                                            <span className="text-white">{space.confidence}%</span>
                                        </div>
                                        <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                                            <div 
                                                className="h-full bg-primary shadow-[0_0_5px_rgba(59,130,246,0.5)] transition-all duration-1000" 
                                                style={{ width: `${space.confidence}%` }}
                                            />
                                        </div>
                                    </div>
                                </td>
                                <td className="px-6 py-4 text-right">
                                    <div className="flex items-center justify-end gap-3">
                                        <button 
                                            onClick={() => onLocateSpace?.(space.id)}
                                            className={`p-2 rounded-md transition-all ${activeSpaceId === space.id ? 'bg-primary text-white' : 'text-text-muted hover:text-white hover:bg-[#1c2128]'}`}
                                            title="Locate on Analysis Map"
                                        >
                                            <MapPin size={14} />
                                        </button>
                                        <button 
                                            onClick={() => {
                                                // Calculate center from geoPolygon or geoBoundingBox
                                                let lat, lng;
                                                if (space.geoPolygon && space.geoPolygon.length > 0) {
                                                    const lats = space.geoPolygon.map(p => p[0]);
                                                    const lngs = space.geoPolygon.map(p => p[1]);
                                                    lat = (Math.min(...lats) + Math.max(...lats)) / 2;
                                                    lng = (Math.min(...lngs) + Math.max(...lngs)) / 2;
                                                } else if (space.geoBoundingBox) {
                                                    lat = (space.geoBoundingBox[0] + space.geoBoundingBox[2]) / 2;
                                                    lng = (space.geoBoundingBox[1] + space.geoBoundingBox[3]) / 2;
                                                }

                                                if (lat && lng) {
                                                    const url = `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
                                                    window.open(url, '_blank');
                                                } else {
                                                    alert("Geospatial coordinates not available for this space.");
                                                }
                                            }}
                                            className="p-2 text-text-muted hover:text-white hover:bg-[#1c2128] rounded-md transition-all"
                                            title="Open in Google Maps"
                                        >
                                            <ExternalLink size={14} />
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        )) : (
                            <tr><td colSpan={9} className="px-6 py-16 text-center text-text-muted italic font-medium opacity-60">No analysis data available. Click "Run Analysis" to begin detection pipeline.</td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default SpacesTable;
import React from 'react';
import { FileJson, FileSpreadsheet, Download, Map, ExternalLink, Globe, LayoutGrid, Maximize2 } from 'lucide-react';
import { LocationInfo, Space } from '../types';
import { convertToGeoJSON, convertToCSV } from '../utils/exportUtils';
import { downloadFile } from '../utils/fileUtils';

interface SidebarInfoProps {
    locationInfo?: LocationInfo | null;
    totalImages: number;
    gridCols: number;
    gridRows: number;
    spaces: Space[];
    municipalityCoverage?: {
        totalBlocks: number;
        areaSqKm: number;
        cols: number;
        rows: number;
        widthKm: number;
        heightKm: number;
    } | null;
    isFetchingLocation?: boolean;
}

const SidebarInfo: React.FC<SidebarInfoProps> = ({ 
    locationInfo, 
    totalImages, 
    gridCols, 
    gridRows, 
    spaces,
    municipalityCoverage, 
    isFetchingLocation 
}) => {
    const handleDownload = (format: string) => {
        if (spaces.length === 0) {
            alert("No data available to export. Run analysis first.");
            return;
        }

        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        
        if (format === 'GeoJSON') {
            const content = convertToGeoJSON(spaces);
            downloadFile(content, `parking-analysis-${timestamp}.geojson`, 'application/geo+json');
        } else if (format === 'CSV') {
            const content = convertToCSV(spaces);
            downloadFile(content, `parking-analysis-${timestamp}.csv`, 'text/csv');
        }
    };

    // Calculate approximate file sizes
    const geojsonSize = spaces.length > 0 
        ? (convertToGeoJSON(spaces).length / 1024).toFixed(1) 
        : "0";
    const csvSize = spaces.length > 0 
        ? (convertToCSV(spaces).length / 1024).toFixed(1) 
        : "0";

    return (
        <div className="lg:col-span-1 w-full flex flex-col gap-6">
            {/* Active Job Scale */}
            <div className="rounded-xl bg-card-dark border border-white/10 p-6 flex flex-col gap-4">
                <div className="flex items-center gap-2">
                    <LayoutGrid size={20} className="text-primary" />
                    <h3 className="text-white font-bold text-lg">Job Scale</h3>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                    <div className="flex flex-col gap-1">
                        <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest flex items-center gap-1">
                            Current Images
                        </span>
                        <span className="text-white text-xl font-black font-mono">
                            {totalImages}
                        </span>
                    </div>
                    <div className="flex flex-col gap-1">
                        <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest flex items-center gap-1">
                            Grid Size
                        </span>
                        <span className="text-white text-xl font-black font-mono">
                            {gridCols} × {gridRows}
                        </span>
                    </div>
                </div>

                <div className="flex flex-col gap-2 mt-2 pt-4 border-t border-white/5">
                    <div className="flex justify-between items-center text-xs">
                        <span className="text-text-muted">Coverage Area</span>
                        <span className="text-white font-medium">~{(totalImages * 0.003).toFixed(3)} km²</span>
                    </div>
                    <p className="text-[9px] text-text-muted mt-1">
                        This reflects the actual area selected for processing in the current job.
                    </p>
                </div>
            </div>

            {/* Municipal Scale Intelligence */}
            {isFetchingLocation ? (
                <div className="rounded-xl bg-card-dark border border-white/5 p-6 flex flex-col items-center justify-center gap-3 min-h-[160px]">
                    <Globe size={24} className="text-primary animate-spin" />
                    <p className="text-sm text-text-muted animate-pulse font-medium">Calculating municipal scale...</p>
                </div>
            ) : municipalityCoverage ? (
                <div className="rounded-xl bg-gradient-to-br from-primary/10 to-transparent border border-primary/20 p-6 flex flex-col gap-4 animate-in slide-in-from-right duration-500">
                    <div className="flex items-center gap-2">
                        <Globe size={20} className="text-primary" />
                        <h3 className="text-white font-bold text-lg">Municipal Scale</h3>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                        <div className="flex flex-col gap-1">
                            <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest flex items-center gap-1">
                                <LayoutGrid size={10} /> Total Images
                            </span>
                            <span className="text-white text-xl font-black font-mono">
                                {municipalityCoverage.totalBlocks.toLocaleString()}
                            </span>
                        </div>
                        <div className="flex flex-col gap-1">
                            <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest flex items-center gap-1">
                                <Maximize2 size={10} /> Land Area
                            </span>
                            <span className="text-white text-xl font-black font-mono">
                                {municipalityCoverage.areaSqKm.toFixed(1)} <span className="text-xs font-normal text-text-muted">km²</span>
                            </span>
                        </div>
                    </div>

                    <div className="flex flex-col gap-2 mt-2 pt-4 border-t border-white/5">
                        <div className="flex justify-between items-center text-xs">
                            <span className="text-text-muted">Bounding Box</span>
                            <span className="text-white font-medium">{municipalityCoverage.widthKm.toFixed(1)}km × {municipalityCoverage.heightKm.toFixed(1)}km</span>
                        </div>
                        <div className="flex justify-between items-center text-xs">
                            <span className="text-text-muted">Processing Grid</span>
                            <span className="text-white font-medium">{municipalityCoverage.cols} × {municipalityCoverage.rows} Blocks</span>
                        </div>
                        <p className="text-[10px] text-primary mt-2 italic">
                            * Scaled for Zoom 21 high-res analysis (56m per block)
                        </p>
                    </div>
                </div>
            ) : (
                <div className="rounded-xl bg-card-dark border border-white/5 p-6 flex flex-col gap-2">
                     <div className="flex items-center gap-2 text-text-muted">
                        <Globe size={18} />
                        <h3 className="font-bold text-sm">Municipal Scale</h3>
                    </div>
                    <p className="text-[10px] text-text-muted italic">
                        Select a municipality to calculate city-wide coverage estimates.
                    </p>
                </div>
            )}

            {/* Location Intelligence (Maps Grounding) */}
            <div className="rounded-xl bg-card-dark border border-white/5 p-6 flex flex-col gap-4">
                <div className="flex items-center gap-2">
                    <Map size={20} className="text-primary" />
                    <h3 className="text-white font-bold text-lg">Location Intelligence</h3>
                </div>
                
                {locationInfo ? (
                    <div className="flex flex-col gap-4 animate-in fade-in duration-500">
                        <p className="text-sm text-gray-300 leading-relaxed">
                            {locationInfo.summary}
                        </p>
                        
                        {locationInfo.chunks && locationInfo.chunks.length > 0 && (
                            <div className="flex flex-col gap-2 mt-2 pt-4 border-t border-white/5">
                                <span className="text-xs font-bold text-text-muted uppercase tracking-wider">Sources</span>
                                {locationInfo.chunks.map((chunk, idx) => {
                                    const source = chunk.maps || chunk.web;
                                    if (!source || !source.uri) return null;
                                    return (
                                        <a 
                                            key={idx}
                                            href={source.uri}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="flex items-center gap-2 text-xs text-[#0bda95] hover:underline truncate"
                                        >
                                            <ExternalLink size={10} />
                                            {source.title || 'Google Maps'}
                                        </a>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                ) : (
                    <p className="text-text-muted text-sm italic">
                        Run analysis to fetch parking insights from Google Maps...
                    </p>
                )}
            </div>

            {/* Downloads Card */}
            <div className="rounded-xl bg-card-dark border border-white/5 p-6 flex flex-col gap-4">
                <h3 className="text-white font-bold text-lg">Results Data</h3>
                <p className="text-text-muted text-sm">Download the processed data for integration with external municipal systems.</p>
                <div className="flex flex-col gap-3 mt-2">
                    <button 
                        onClick={() => handleDownload('GeoJSON')}
                        className="group flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 border border-white/5 transition-all"
                    >
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-[#2d2222] rounded text-[#0bda95]">
                                <FileJson size={20} />
                            </div>
                            <div className="flex flex-col items-start">
                                <span className="text-white text-sm font-bold">GeoJSON</span>
                                <span className="text-text-muted text-xs">Vector data ({geojsonSize} KB)</span>
                            </div>
                        </div>
                        <Download size={18} className="text-text-muted group-hover:text-white" />
                    </button>
                    <button 
                        onClick={() => handleDownload('CSV')}
                        className="group flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 border border-white/5 transition-all"
                    >
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-[#2d2222] rounded text-primary">
                                <FileSpreadsheet size={20} />
                            </div>
                            <div className="flex flex-col items-start">
                                <span className="text-white text-sm font-bold">CSV Report</span>
                                <span className="text-text-muted text-xs">Spreadsheet ({csvSize} KB)</span>
                            </div>
                        </div>
                        <Download size={18} className="text-text-muted group-hover:text-white" />
                    </button>
                </div>
            </div>

            {/* Job Information */}
            <div className="rounded-xl bg-card-dark border border-white/5 p-6 flex-1">
                <h3 className="text-white font-bold text-lg mb-4">Job Information</h3>
                <div className="flex flex-col gap-4">
                    <div className="flex justify-between items-center py-2 border-b border-white/5">
                        <span className="text-text-muted text-sm">Created At</span>
                        <span className="text-white text-sm font-mono">Oct 24, 14:00</span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-white/5">
                        <span className="text-text-muted text-sm">Completed At</span>
                        <span className="text-white text-sm font-mono">Oct 24, 14:05</span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-white/5">
                        <span className="text-text-muted text-sm">Source ID</span>
                        <span className="text-white text-sm font-mono">IMG_8842_NL</span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-white/5">
                        <span className="text-text-muted text-sm">Resolution</span>
                        <span className="text-white text-sm font-mono">10cm / px</span>
                    </div>
                    <div className="flex justify-between items-center py-2">
                        <span className="text-text-muted text-sm">Model Version</span>
                        <span className="inline-flex items-center rounded bg-white/10 px-2 py-0.5 text-xs font-medium text-white">v2.4.1-stable</span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SidebarInfo;
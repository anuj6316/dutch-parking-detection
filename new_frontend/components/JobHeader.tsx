import React, { useState, useEffect, useRef } from 'react';
import { ChevronRight, RefreshCw, Download, RotateCcw, PenTool, List, MapPin, Settings, X } from 'lucide-react';
import SearchableSelect from './SearchableSelect';

export interface Area {
    id: string;
    name: string;
    bbox: string;
}

interface JobHeaderProps {
    onRerun: () => void;
    onTerminate?: () => void;
    onExport?: (format: 'GeoJSON' | 'CSV') => void;
    isAnalyzing: boolean;
    onBack: () => void;
    areas: Area[];
    selectedAreaId: string;
    onAreaChange: (id: string) => void;
    detectionConfidence: number;
    setDetectionConfidence: (confidence: number) => void;
    useCustomArea: boolean;
    onToggleCustomArea: () => void;
    onEditCustomArea?: () => void;
    customAreaName?: string;
    totalImages: number;
    setTotalImages: (count: number) => void;
}

const JobHeader: React.FC<JobHeaderProps> = ({
    onRerun,
    onTerminate,
    onExport,
    isAnalyzing,
    onBack,
    areas,
    selectedAreaId,
    onAreaChange,
    detectionConfidence,
    setDetectionConfidence,
    useCustomArea,
    onToggleCustomArea,
    onEditCustomArea,
    customAreaName,
    totalImages,
    setTotalImages
}) => {
    const selectedArea = areas.find(a => a.id === selectedAreaId);
    const displayName = useCustomArea ? (customAreaName || 'Custom Area') : (selectedArea?.name || 'Unknown Location');
    const [showAdvanced, setShowAdvanced] = useState(false);
    const advancedRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (advancedRef.current && !advancedRef.current.contains(event.target as Node)) {
                setShowAdvanced(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    return (
        <div className="flex flex-col gap-6 relative z-[500]">
            <div className="flex items-center gap-2 text-xs font-medium text-text-muted">
                <button onClick={onBack} className="hover:text-white transition-colors">Dashboard</button>
                <ChevronRight size={14} />
                <span>Jobs</span>
                <ChevronRight size={14} />
                <span className="text-white font-mono uppercase tracking-wider font-bold">#{selectedAreaId.toUpperCase()}</span>
            </div>

            <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
                <div className="flex flex-col gap-3">
                    <div className="flex items-center gap-4">
                        <h1 className="text-white text-3xl font-bold font-display tracking-tight leading-none">{displayName}</h1>
                        <span className="bg-success/10 text-success text-[10px] font-bold uppercase tracking-widest border border-success/20 px-2.5 py-1 rounded-full">
                            Active Monitoring
                        </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-6 text-sm text-text-muted">
                        <div className="flex items-center gap-2">
                            <span className="size-2 rounded-full bg-primary animate-pulse"></span>
                            <span className="text-xs font-medium">YOLO OBB Detection</span>
                        </div>

                        <div className="flex bg-[#1c2128] rounded-full border border-card-border overflow-hidden p-0.5">
                            <button 
                                onClick={() => useCustomArea && onToggleCustomArea()}
                                className={`flex items-center gap-2 px-4 py-1 rounded-full text-[10px] font-bold transition-all uppercase tracking-wider ${!useCustomArea ? 'bg-primary text-white shadow-lg' : 'text-text-muted hover:text-white'}`}
                            >
                                <List size={12} /> Predefined
                            </button>
                            <button 
                                onClick={() => useCustomArea ? onEditCustomArea?.() : onToggleCustomArea()}
                                className={`flex items-center gap-2 px-4 py-1 rounded-full text-[10px] font-bold transition-all uppercase tracking-wider ${useCustomArea ? 'bg-primary text-white shadow-lg' : 'text-text-muted hover:text-white'}`}
                            >
                                <PenTool size={12} /> {useCustomArea ? 'Edit Area' : 'Custom Area'}
                            </button>
                        </div>

                        {!useCustomArea && (
                            <div className="relative">
                                <SearchableSelect
                                    options={areas.map(a => ({ id: a.id, label: a.name }))}
                                    value={selectedAreaId}
                                    onChange={onAreaChange}
                                    placeholder="Select municipality..."
                                    className="bg-[#1c2128] border border-card-border rounded-lg min-w-[220px] hover:border-primary/50"
                                    leadingIcon={<MapPin size={14} className="text-primary shrink-0" />}
                                />
                            </div>
                        )}

                        <div className="relative" ref={advancedRef}>
                            <button
                                onClick={() => setShowAdvanced(!showAdvanced)}
                                className={`flex items-center gap-2 p-2 rounded-lg border transition-all ${
                                    showAdvanced 
                                    ? 'bg-primary/20 border-primary text-white' 
                                    : 'bg-[#1c2128] border-card-border text-text-muted hover:text-white hover:border-white/20'
                                }`}
                                title="Advanced Options"
                            >
                                <Settings size={16} />
                            </button>

                            {showAdvanced && (
                                <div className="absolute top-full mt-2 right-0 bg-[#1c2128] border border-card-border rounded-xl p-5 shadow-2xl z-[1000] w-80 animate-in fade-in slide-in-from-top-2 duration-200">
                                    <div className="flex items-center justify-between mb-4">
                                        <h3 className="text-white text-xs font-bold uppercase tracking-widest">Advanced Settings</h3>
                                        <Settings size={12} className="text-primary/50" />
                                    </div>
                                    
                                    <div className="flex flex-col gap-5">
                                        <div className="flex flex-col gap-3">
                                            <div className="flex justify-between items-center">
                                                <label htmlFor="confidence-threshold" className="text-text-muted text-xs font-medium">Confidence Threshold</label>
                                                <span className="bg-primary/10 text-primary text-[10px] px-2 py-0.5 rounded font-mono font-bold border border-primary/20">
                                                    {Math.round(detectionConfidence * 100)}%
                                                </span>
                                            </div>
                                            <input
                                                type="range"
                                                id="confidence-threshold"
                                                min="0.0"
                                                max="1.0"
                                                step="0.05"
                                                value={detectionConfidence}
                                                onChange={(e) => setDetectionConfidence(parseFloat(e.target.value))}
                                                className="w-full h-1.5 rounded-lg appearance-none cursor-pointer bg-white/5 accent-primary hover:accent-primary/80 transition-all"
                                                disabled={isAnalyzing}
                                            />
                                            <div className="flex justify-between text-[9px] text-white/20 font-mono tracking-tighter">
                                                <span>LOOSE</span>
                                                <span>BALANCED</span>
                                                <span>STRICT</span>
                                            </div>
                                        </div>

                                        <div className="flex flex-col gap-4 border-t border-white/5 pt-5">
                                            <div className="flex justify-between items-center">
                                                <div className="flex flex-col gap-0.5">
                                                    <label htmlFor="total-images" className="text-text-muted text-xs font-medium uppercase tracking-wider">Analysis Scale</label>
                                                    <span className="text-[9px] text-primary/60 font-medium">
                                                        {useCustomArea ? "Auto-calculated from area" : "Number of images to process"}
                                                    </span>
                                                </div>
                                                <div className={`flex items-center bg-black/40 border border-white/10 rounded-lg p-1 group-focus-within:border-primary/50 transition-all ${useCustomArea ? 'opacity-50' : ''}`}>
                                                    <input 
                                                        type="number"
                                                        id="total-images-input"
                                                        value={totalImages}
                                                        onChange={(e) => setTotalImages(Math.max(1, Math.min(1000, parseInt(e.target.value) || 1)))}
                                                        className="w-16 bg-transparent border-none text-xs text-white text-center focus:ring-0 py-0.5 font-mono font-bold"
                                                        disabled={isAnalyzing || useCustomArea}
                                                    />
                                                </div>
                                            </div>
                                            
                                            <input
                                                type="range"
                                                id="total-images"
                                                min="1"
                                                max="1000"
                                                step="1"
                                                value={totalImages}
                                                onChange={(e) => setTotalImages(parseInt(e.target.value))}
                                                className={`w-full h-1.5 rounded-lg appearance-none cursor-pointer bg-white/5 accent-primary hover:accent-primary/80 transition-all ${useCustomArea ? 'opacity-50 cursor-not-allowed' : ''}`}
                                                disabled={isAnalyzing || useCustomArea}
                                            />
                                            
                                            <div className="flex justify-between text-[9px] text-white/20 font-mono">
                                                <span>1 IMG</span>
                                                <span>500 IMGS</span>
                                                <span>1K IMGS</span>
                                            </div>

                                            <div className="p-3 bg-white/5 rounded-lg border border-white/5">
                                                <p className="text-[10px] text-text-muted leading-relaxed">
                                                    Analysis will generate a dynamic grid covering approx. 
                                                    <span className="text-white font-bold mx-1">
                                                        {(totalImages * 0.003).toFixed(2)} km²
                                                    </span> 
                                                    around the center point.
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>


                    </div>
                </div>

                <div className="flex items-center gap-3">
                    {isAnalyzing ? (
                        <button 
                            onClick={onTerminate} 
                            className="flex items-center gap-2 bg-red-500/10 border border-red-500/20 text-red-500 px-5 py-2.5 rounded-lg text-sm font-bold hover:bg-red-500/20 transition-all"
                        >
                            <X size={16} /> Terminate
                        </button>
                    ) : (
                        <button 
                            onClick={onRerun} 
                            className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white px-5 py-2.5 rounded-lg text-sm font-bold shadow-lg shadow-primary/30 transition-all"
                        >
                            <RefreshCw size={16} /> Run Analysis
                        </button>
                    )}
                    <button 
                        className="flex items-center gap-2 bg-[#1c2128] border border-card-border text-white px-5 py-2.5 rounded-lg text-sm font-bold hover:bg-white/5 transition-all"
                    >
                        <RotateCcw size={16} /> Re-run
                    </button>
                    <button 
                        onClick={() => onExport?.('GeoJSON')}
                        className="flex items-center gap-2 bg-[#1c2128] border border-card-border text-white px-5 py-2.5 rounded-lg text-sm font-bold hover:bg-white/5 transition-all"
                    >
                        <Download size={16} /> Export Data
                    </button>
                </div>
            </div>
        </div>
    );
};

export default JobHeader;
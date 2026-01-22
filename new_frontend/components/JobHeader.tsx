import React from 'react';
import { ChevronRight, RefreshCw, Download, RotateCcw, PenTool, List, MapPin } from 'lucide-react';
import SearchableSelect from './SearchableSelect';

export interface Area {
    id: string;
    name: string;
    bbox: string;
}

interface JobHeaderProps {
    onRerun: () => void;
    isAnalyzing: boolean;
    onBack: () => void;
    areas: Area[];
    selectedAreaId: string;
    onAreaChange: (id: string) => void;
    detectionConfidence: number;
    setDetectionConfidence: (confidence: number) => void;
    useCustomArea: boolean;
    onToggleCustomArea: () => void;
    customAreaName?: string;
}

const JobHeader: React.FC<JobHeaderProps> = ({
    onRerun,
    isAnalyzing,
    onBack,
    areas,
    selectedAreaId,
    onAreaChange,
    detectionConfidence,
    setDetectionConfidence,
    useCustomArea,
    onToggleCustomArea,
    customAreaName
}) => {
    const selectedArea = areas.find(a => a.id === selectedAreaId);
    const displayName = useCustomArea ? (customAreaName || 'Custom Area') : (selectedArea?.name || 'Unknown Location');

    return (
        <div className="flex flex-col gap-6 relative z-[2000]">
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
                                onClick={() => !useCustomArea && onToggleCustomArea()}
                                className={`flex items-center gap-2 px-4 py-1 rounded-full text-[10px] font-bold transition-all uppercase tracking-wider ${useCustomArea ? 'bg-primary text-white shadow-lg' : 'text-text-muted hover:text-white'}`}
                            >
                                <PenTool size={12} /> Custom Area
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

                        <div className="flex items-center gap-2">
                            <label htmlFor="confidence-threshold" className="text-text-muted text-sm font-medium">Confidence:</label>
                            <input
                                type="range"
                                id="confidence-threshold"
                                min="0.0"
                                max="1.0"
                                step="0.05"
                                value={detectionConfidence}
                                onChange={(e) => setDetectionConfidence(parseFloat(e.target.value))}
                                className="w-24 h-2 rounded-lg appearance-none cursor-pointer bg-primary/50 accent-primary"
                                disabled={isAnalyzing}
                            />
                            <span className="text-white text-sm font-mono">{detectionConfidence.toFixed(2)}</span>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <button 
                        onClick={onRerun} 
                        className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white px-5 py-2.5 rounded-lg text-sm font-bold shadow-lg shadow-primary/30 transition-all"
                    >
                        <RefreshCw size={16} className={isAnalyzing ? 'animate-spin' : ''} />
                        Run Analysis
                    </button>
                    <button 
                        className="flex items-center gap-2 bg-[#1c2128] border border-card-border text-white px-5 py-2.5 rounded-lg text-sm font-bold hover:bg-white/5 transition-all"
                    >
                        <RotateCcw size={16} /> Re-run
                    </button>
                    <button 
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
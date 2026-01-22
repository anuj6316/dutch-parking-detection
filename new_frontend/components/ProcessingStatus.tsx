
import React, { useState } from 'react';
import { CheckCircle2, Loader2, Upload, FileCog, BrainCircuit, FileJson, Image as ImageIcon, Terminal, ScanSearch, ChevronDown, ChevronUp, Car } from 'lucide-react';
import { Space } from '../types';
import TileComparisonSlider from './TileComparisonSlider';
import SpaceComparisonSlider from './SpaceComparisonSlider';

export type ProcessingStep = 'idle' | 'uploading' | 'preprocessing' | 'analyzing' | 'classifying' | 'finalizing' | 'completed';

interface ProcessingStatusProps {
    status: ProcessingStep;
    images?: string[];
    maskedImages?: Map<number, string[]>;
    statusDetails?: string;
    spaces?: Space[];
    logs?: string[];
}

const ProcessingStatus: React.FC<ProcessingStatusProps> = ({ status, images = [], maskedImages, statusDetails, spaces = [], logs = [] }) => {
    const [expanded, setExpanded] = useState(false);
    const [activeSection, setActiveSection] = useState<string | null>('tiles');

    const steps = [
        { id: 'uploading', label: 'FETCH MAP', icon: Upload },
        { id: 'preprocessing', label: 'PREPROCESSING', icon: FileCog },
        { id: 'analyzing', label: 'SPOT DETECTION', icon: ScanSearch },
        { id: 'classifying', label: 'OCCUPANCY CHECK', icon: BrainCircuit },
        { id: 'finalizing', label: 'FINALIZING', icon: FileJson }
    ];

    const toggleSection = (section: string) => {
        setActiveSection(activeSection === section ? null : section);
    };

    return (
        <div className="bg-card border border-card-border rounded-xl overflow-hidden shadow-sm">
            <button 
                onClick={() => setExpanded(!expanded)}
                className="w-full px-6 py-4 flex items-center justify-between bg-white/5 border-b border-card-border hover:bg-white/10 transition-all"
            >
                <div className="flex items-center gap-3">
                    <Terminal size={18} className="text-primary" />
                    <span className="text-white font-bold text-sm tracking-tight uppercase">Pipeline Status</span>
                </div>
                {expanded ? <ChevronUp size={18} className="text-text-muted" /> : <ChevronDown size={18} className="text-text-muted" />}
            </button>

            {expanded && (
                <div className="p-6 flex flex-col gap-8 animate-in fade-in duration-300">
                    <div className="flex flex-col gap-4">
                        <div className="flex justify-between items-end">
                            <div className="flex items-center gap-2 text-primary text-[10px] font-bold uppercase tracking-widest">
                                {status === 'completed' ? (
                                    <span className="text-success flex items-center gap-2">
                                        <CheckCircle2 size={16} /> ANALYSIS COMPLETE
                                    </span>
                                ) : (
                                    <span className="flex items-center gap-2 text-primary">
                                        <Loader2 size={16} className="animate-spin" /> {status.toUpperCase()}...
                                    </span>
                                )}
                            </div>
                            <span className="text-white font-mono text-sm font-bold">{status === 'completed' ? '100%' : status === 'idle' ? '0%' : '80%'}</span>
                        </div>
                        <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                            <div 
                                className={`h-full transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(59,130,246,0.5)] ${status === 'completed' ? 'bg-success shadow-[0_0_10px_rgba(63,185,80,0.5)]' : 'bg-primary'}`}
                                style={{ width: status === 'completed' ? '100%' : status === 'idle' ? '0%' : '80%' }}
                            />
                        </div>
                        {statusDetails && <p className="text-[10px] text-text-muted italic">{statusDetails}</p>}
                    </div>

                    <div className="grid grid-cols-5 gap-4 relative">
                        {/* Connecting Line */}
                        <div className="absolute top-5 left-[10%] right-[10%] h-[1px] bg-card-border z-0" />
                        
                        {steps.map((step) => {
                            const stepActive = status === step.id || (status === 'completed');
                            const Icon = step.icon;
                            return (
                                <div key={step.id} className={`flex flex-col items-center gap-3 transition-all relative z-10 ${stepActive ? 'opacity-100' : 'opacity-30'}`}>
                                    <div className={`p-2 rounded-full ${stepActive ? 'bg-primary/20 text-primary border border-primary/40' : 'bg-card text-text-muted border border-card-border'}`}>
                                        <Icon size={18} />
                                    </div>
                                    <span className="text-[9px] font-bold text-text-muted uppercase tracking-[0.15em] text-center">{step.label}</span>
                                </div>
                            );
                        })}
                    </div>

                    <div className="flex flex-col gap-2 border-t border-card-border pt-4">
                        <CollapsibleItem 
                            label={`PIPELINE LOGS (${logs.length})`} 
                            icon={<Terminal size={14} />} 
                            isOpen={activeSection === 'logs'} 
                            onClick={() => toggleSection('logs')}
                        >
                            <div className="bg-black/40 rounded-lg p-3 font-mono text-[10px] text-primary h-32 overflow-y-auto border border-card-border">
                                {logs.map((log, i) => <div key={i} className="mb-1 opacity-80">{log}</div>)}
                            </div>
                        </CollapsibleItem>

                        <CollapsibleItem 
                            label={`AI INPUT STREAM (${images.length}x TILES)`} 
                            icon={<ImageIcon size={14} />} 
                            isOpen={activeSection === 'tiles'} 
                            onClick={() => toggleSection('tiles')}
                        >
                            <TileComparisonSlider images={images} maskedImages={maskedImages} />
                        </CollapsibleItem>

                        <CollapsibleItem 
                            label={`VEHICLE DETECTION (${spaces?.length || 0}x SPACES)`} 
                            icon={<Car size={14} />} 
                            isOpen={activeSection === 'spaces'} 
                            onClick={() => toggleSection('spaces')}
                        >
                            <SpaceComparisonSlider spaces={spaces} />
                        </CollapsibleItem>
                    </div>
                </div>
            )}
        </div>
    );
};

const CollapsibleItem = ({ label, icon, isOpen, onClick, children }: any) => (
    <div className="flex flex-col rounded-lg transition-all">
        <button onClick={onClick} className="flex items-center gap-3 py-3 text-text-muted hover:text-white transition-colors">
            <div className={`p-1 rounded transition-all ${isOpen ? 'bg-primary text-white rotate-180' : 'bg-white/5'}`}>
                <ChevronDown size={14} />
            </div>
            <div className="flex items-center gap-2">
                {icon}
                <span className="text-[10px] font-bold uppercase tracking-[0.1em]">{label}</span>
            </div>
        </button>
        {isOpen && <div className="pl-6 pb-4 animate-in slide-in-from-top-1">{children}</div>}
    </div>
);

export default ProcessingStatus;

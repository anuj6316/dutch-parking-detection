import React from 'react';
import { PieChart, ParkingSquare, Car, CheckCircle2 } from 'lucide-react';
import { JobMetrics } from '../types';

interface StatsCardsProps {
    metrics: JobMetrics;
}

const StatsCards: React.FC<StatsCardsProps> = ({ metrics }) => {
    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-card border border-card-border rounded-xl p-5 flex items-center justify-between">
                <div className="flex flex-col gap-1">
                    <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest">Occupancy Rate</span>
                    <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-bold text-white">{metrics.occupancyRate}%</span>
                        <span className="text-success text-xs font-medium">Available</span>
                    </div>
                </div>
                <div className="relative size-14">
                    <svg className="size-full transform -rotate-90">
                        <circle cx="28" cy="28" r="24" stroke="currentColor" strokeWidth="4" fill="transparent" className="text-white/5" />
                        <circle 
                            cx="28" cy="28" r="24" stroke="currentColor" strokeWidth="4" fill="transparent" 
                            strokeDasharray={150.8}
                            strokeDashoffset={150.8 - (150.8 * metrics.occupancyRate) / 100}
                            className="text-primary transition-all duration-1000 ease-out"
                        />
                    </svg>
                </div>
            </div>

            <div className="bg-card border border-card-border rounded-xl p-5 flex items-center justify-between">
                <div className="flex flex-col gap-1">
                    <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest">Total Capacity</span>
                    <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-bold text-white">{metrics.totalSpaces}</span>
                        <span className="text-text-muted text-xs">spots</span>
                    </div>
                </div>
                <div className="size-12 bg-white/5 rounded-lg flex items-center justify-center text-text-muted">
                    <ParkingSquare size={24} />
                </div>
            </div>

            <div className="bg-card border border-card-border rounded-xl p-5 flex items-center justify-between">
                <div className="flex flex-col gap-1">
                    <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest">Vehicles Detected</span>
                    <span className="text-3xl font-bold text-white">{metrics.occupiedCount}</span>
                </div>
                <div className="size-12 bg-primary/10 rounded-lg flex items-center justify-center text-primary">
                    <Car size={24} />
                </div>
            </div>

            <div className="bg-card border border-card-border rounded-xl p-5 flex items-center justify-between">
                <div className="flex flex-col gap-1">
                    <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest">Available Spots</span>
                    <span className="text-3xl font-bold text-white">{metrics.emptyCount}</span>
                </div>
                <div className="size-12 bg-success/10 rounded-lg flex items-center justify-center text-success">
                    <CheckCircle2 size={24} />
                </div>
            </div>
        </div>
    );
};

export default StatsCards;
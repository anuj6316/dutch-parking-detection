import React from 'react';
import { ArrowRight, Activity, Calendar, MapPin, CheckCircle2, Clock } from 'lucide-react';

interface DashboardProps {
  onNavigateJob: () => void;
}

const recentJobs = [
  { id: 'JOB-NL-GEMINI-V1', location: 'Utrecht Central Zone A', status: 'Active', date: 'Just now', spaces: 12, occupancy: '66%' },
  { id: 'JOB-NL-428', location: 'Amersfoort Station', status: 'Completed', date: '2 hours ago', spaces: 45, occupancy: '82%' },
  { id: 'JOB-NL-425', location: 'Rotterdam Blaak', status: 'Completed', date: 'Yesterday', spaces: 120, occupancy: '94%' },
  { id: 'JOB-NL-422', location: 'Amsterdam Noord P+R', status: 'Completed', date: 'Oct 23', spaces: 350, occupancy: '45%' },
];

const Dashboard: React.FC<DashboardProps> = ({ onNavigateJob }) => {
  return (
    <div className="w-full max-w-[1400px] flex flex-col gap-8">
      
      {/* Welcome Section */}
      <div className="flex flex-col gap-2">
        <h1 className="text-white text-3xl md:text-4xl font-black leading-tight tracking-[-0.033em]">Dashboard</h1>
        <p className="text-text-muted text-base font-normal">Overview of your recent parking detection operations.</p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-card-dark p-6 rounded-xl border border-white/5 flex flex-col gap-2">
            <div className="flex items-center gap-2 text-text-muted mb-2">
                <Activity size={20} />
                <span className="text-sm font-bold uppercase tracking-wider">Active Jobs</span>
            </div>
            <span className="text-3xl font-bold text-white">1</span>
            <span className="text-sm text-[#0bda95]">System operational</span>
        </div>
        <div className="bg-card-dark p-6 rounded-xl border border-white/5 flex flex-col gap-2">
            <div className="flex items-center gap-2 text-text-muted mb-2">
                <CheckCircle2 size={20} />
                <span className="text-sm font-bold uppercase tracking-wider">Completed Today</span>
            </div>
            <span className="text-3xl font-bold text-white">14</span>
            <span className="text-sm text-text-muted">Target: 20</span>
        </div>
        <div className="bg-card-dark p-6 rounded-xl border border-white/5 flex flex-col gap-2">
            <div className="flex items-center gap-2 text-text-muted mb-2">
                <MapPin size={20} />
                <span className="text-sm font-bold uppercase tracking-wider">Locations Monitored</span>
            </div>
            <span className="text-3xl font-bold text-white">8</span>
            <span className="text-sm text-text-muted">Across 3 cities</span>
        </div>
      </div>

      {/* Recent Jobs Table */}
      <div className="rounded-xl bg-card-dark border border-white/5 overflow-hidden">
        <div className="p-6 border-b border-white/5">
            <h3 className="text-white font-bold text-lg">Recent Analysis Jobs</h3>
        </div>
        <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
                <thead className="bg-card-lighter text-xs uppercase font-semibold text-text-muted tracking-wider">
                    <tr>
                        <th className="px-6 py-4 font-bold border-b border-white/5">Job ID</th>
                        <th className="px-6 py-4 font-bold border-b border-white/5">Location</th>
                        <th className="px-6 py-4 font-bold border-b border-white/5">Date</th>
                        <th className="px-6 py-4 font-bold border-b border-white/5">Status</th>
                        <th className="px-6 py-4 font-bold border-b border-white/5 text-right">Action</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-sm">
                    {recentJobs.map((job) => (
                        <tr 
                            key={job.id} 
                            onClick={() => onNavigateJob()}
                            className="group hover:bg-white/5 transition-colors cursor-pointer"
                        >
                            <td className="px-6 py-4 font-mono font-medium text-primary group-hover:text-white transition-colors">
                                {job.id}
                            </td>
                            <td className="px-6 py-4 text-white">
                                {job.location}
                            </td>
                            <td className="px-6 py-4 text-text-muted flex items-center gap-2">
                                <Calendar size={14} />
                                {job.date}
                            </td>
                            <td className="px-6 py-4">
                                <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${
                                    job.status === 'Active' 
                                    ? 'bg-[#0bda95]/10 text-[#0bda95] ring-[#0bda95]/20' 
                                    : 'bg-white/5 text-text-muted ring-white/10'
                                }`}>
                                    {job.status}
                                </span>
                            </td>
                            <td className="px-6 py-4 text-right">
                                <button 
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onNavigateJob();
                                    }}
                                    className="text-text-muted group-hover:text-white transition-colors"
                                >
                                    <ArrowRight size={18} />
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
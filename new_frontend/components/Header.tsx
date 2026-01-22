import React from 'react';
import { Car, Search } from 'lucide-react';

interface HeaderProps {
    onNavigate: (view: 'dashboard' | 'job') => void;
    currentView: 'dashboard' | 'job';
}

const Header: React.FC<HeaderProps> = ({ onNavigate, currentView }) => {
    return (
        <div className="border-b border-card-border px-4 md:px-10 py-3 bg-background sticky top-0 z-[6000]">
            <header className="flex items-center justify-between whitespace-nowrap mx-auto max-w-[1400px]">
                <div 
                    className="flex items-center gap-3 cursor-pointer group"
                    onClick={() => onNavigate('dashboard')}
                >
                    <div className="size-8 bg-primary/20 text-primary rounded-lg flex items-center justify-center group-hover:bg-primary group-hover:text-white transition-all">
                        <Car size={20} />
                    </div>
                    <h2 className="text-white text-lg font-bold leading-tight tracking-tight">Dutch Parking Detection</h2>
                </div>
                
                <nav className="hidden md:flex flex-1 justify-end items-center gap-8">
                    <div className="flex items-center gap-8 mr-8">
                        {['Dashboard', 'Jobs', 'Map View', 'Settings'].map((item) => (
                            <button 
                                key={item}
                                onClick={() => item === 'Dashboard' ? onNavigate('dashboard') : onNavigate('job')}
                                className={`text-sm font-medium transition-colors ${
                                    (currentView === 'dashboard' && item === 'Dashboard') || 
                                    (currentView === 'job' && item === 'Jobs')
                                    ? 'text-white border-b-2 border-primary pb-1' 
                                    : 'text-text-muted hover:text-white pb-1 border-b-2 border-transparent'
                                }`}
                            >
                                {item}
                            </button>
                        ))}
                    </div>
                    
                    <div className="flex items-center gap-4">
                        <button className="text-text-muted hover:text-white">
                            <Search size={20} />
                        </button>
                        <div 
                            className="size-9 bg-gradient-to-br from-primary to-indigo-600 rounded-full border border-white/20 cursor-pointer shadow-lg overflow-hidden"
                        >
                            <img src="https://lh3.googleusercontent.com/aida-public/AB6AXuBB3CRJI0Lw2SFUu4Eri863TD-C_r1TK7yE-lTMrNyE3GKs0dSkJmU4NjMfwnJB5s1TPgQKbi-hsUxQahpEXHPw1zfPQBak0wcAxKl2R0e-dg7tTV2GUD1VOeeJBDHXm0mmFlZx6wxbwS3RxMfY_26N3YnKH-wYAoIcx4eLxg4RqQgPYyOFQo8YCA4A5EZADEPyDtpXPoujuLciG2DB5MzVOaSTUta4jdMR_ICl7uY_RoIEeYyPqIpjpIypjnMEQZQdU6jy_nh71Btc" className="w-full h-full object-cover" alt="Profile" />
                        </div>
                    </div>
                </nav>
            </header>
        </div>
    );
};

export default Header;
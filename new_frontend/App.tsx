import React, { useState } from 'react';
import Header from './components/Header';
import Dashboard from './components/Dashboard';
import JobView from './components/JobView';

const App: React.FC = () => {
    const [currentView, setCurrentView] = useState<'dashboard' | 'job'>('job');

    const navigateToDashboard = () => setCurrentView('dashboard');
    const navigateToJob = () => setCurrentView('job');

    return (
        <div className="flex flex-col min-h-screen bg-background-light dark:bg-background-dark">
            <Header onNavigate={setCurrentView} currentView={currentView} />
            <div className="flex-1 flex justify-center py-8 px-4 md:px-10">
                {currentView === 'dashboard' ? (
                    <Dashboard onNavigateJob={navigateToJob} />
                ) : (
                    <JobView onBack={navigateToDashboard} />
                )}
            </div>
        </div>
    );
};

export default App;
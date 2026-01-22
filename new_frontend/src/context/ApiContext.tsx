import React, { createContext, useContext, ReactNode } from 'react';
import { analyzeTiles, checkHealth, AnalysisRequest, AnalysisResponse } from '../api/parkingApi';

interface ApiContextType {
  analyzeTiles: (data: AnalysisRequest) => Promise<AnalysisResponse>;
  checkHealth: () => Promise<{ status: string }>;
}

const ApiContext = createContext<ApiContextType | undefined>(undefined);

export const ApiProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  return (
    <ApiContext.Provider value={{ analyzeTiles, checkHealth }}>
      {children}
    </ApiContext.Provider>
  );
};

export const useApi = (): ApiContextType => {
  const context = useContext(ApiContext);
  if (context === undefined) {
    throw new Error('useApi must be used within an ApiProvider');
  }
  return context;
};

import { API_ENDPOINTS, DEFAULT_REQUEST_HEADERS } from './config';

export interface TilePayload {
  image_base64: string;
  tile_index: number;
  bounds: {
    _southWest: { lat: number; lng: number };
    _northEast: { lat: number; lng: number };
  };
}

export interface AnalysisRequest {
  tiles: TilePayload[];
  confidence_threshold: number;
  count_vehicles: boolean;
}

export interface AnalysisResponse {
  results: any[]; // Adjust this based on your actual response type
}

export const analyzeTiles = async (data: AnalysisRequest): Promise<AnalysisResponse> => {
  try {
    const response = await fetch(API_ENDPOINTS.ANALYZE_TILES, {
      method: 'POST',
      headers: DEFAULT_REQUEST_HEADERS,
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error analyzing tiles:', error);
    throw error;
  }
};

export const analyzeTilesStream = async (data: AnalysisRequest): Promise<Response> => {
    const response = await fetch(API_ENDPOINTS.ANALYZE_TILES_STREAM, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    
    if (!response.ok) {
        throw new Error(`Analysis failed: ${response.status}`);
    }
    
    return response;
};

export const checkHealth = async (): Promise<{ status: string }> => {
  try {
    const response = await fetch(API_ENDPOINTS.HEALTH, {
      headers: DEFAULT_REQUEST_HEADERS,
    });

    if (!response.ok) {
      throw new Error(`Health check failed with status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Health check error:', error);
    throw error;
  }
};

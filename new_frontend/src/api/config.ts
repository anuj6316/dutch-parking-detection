const API_BASE_URL = 'http://localhost:8000'
// 'https://demo.backend.aishree.com';

const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

export const API_ENDPOINTS = {
  ANALYZE_TILES: `${API_BASE_URL}/analyze-tiles/`,
  CANCEL_ANALYSIS: `${API_BASE_URL}/cancel-analysis/`,
  ANALYZE_TILES_STREAM: `${API_BASE_URL}/analyze-tiles-stream/`,
  ANALYZE_TILES_WS: `${WS_BASE_URL}/ws/analyze-tiles`,
  ANALYZE_LOGS_WS: `${WS_BASE_URL}/ws/logs/`,
  HEALTH: `${API_BASE_URL}/health/`,
  SAVE_IMAGES: `${API_BASE_URL}/save-images/`,
};

export const SAVE_IMAGES_ENABLED = true; // Set to false for deployment

export const DEFAULT_REQUEST_HEADERS = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
};

const API_BASE_URL = 'http://localhost:8000'
// 'https://demo.backend.aishree.com';

export const API_ENDPOINTS = {
  ANALYZE_TILES: `${API_BASE_URL}/analyze-tiles/`,
  ANALYZE_TILES_STREAM: `${API_BASE_URL}/analyze-tiles-stream/`,
  HEALTH: `${API_BASE_URL}/health/`,
  SAVE_IMAGES: `${API_BASE_URL}/save-images/`,
};

export const SAVE_IMAGES_ENABLED = true; // Set to false for deployment

export const DEFAULT_REQUEST_HEADERS = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
};

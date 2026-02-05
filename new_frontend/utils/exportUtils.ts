import { Space } from '../types';

/**
 * Converts a list of Space objects into a standard GeoJSON FeatureCollection.
 * Note: GeoJSON uses [longitude, latitude] order.
 */
export const convertToGeoJSON = (spaces: Space[]): string => {
  const features = spaces
    .filter(space => space.geoPolygon && space.geoPolygon.length > 0)
    .map(space => {
      // Flip [lat, lng] to [lng, lat] for GeoJSON spec
      const coordinates = [space.geoPolygon!.map(p => [p[1], p[0]])];
      
      return {
        type: 'Feature',
        properties: {
          id: space.id,
          status: space.status,
          confidence: space.confidence,
          vehicleCount: space.vehicleCount || 0,
          areaSqMeters: space.areaSqMeters || 0,
          estimatedCapacity: space.estimatedCapacity || 1,
          tileIndex: space.tileIndex
        },
        geometry: {
          type: 'Polygon',
          coordinates: coordinates
        }
      };
    });

  const collection = {
    type: 'FeatureCollection',
    features: features
  };

  return JSON.stringify(collection, null, 2);
};

/**
 * Converts a list of Space objects into a CSV string.
 */
export const convertToCSV = (spaces: Space[]): string => {
  if (spaces.length === 0) return '';

  const headers = [
    'Space ID',
    'Status',
    'Confidence (%)',
    'Vehicle Count',
    'Area (sqm)',
    'Estimated Capacity',
    'Center Latitude',
    'Center Longitude'
  ];

  const rows = spaces.map(space => {
    let centerLat = '';
    let centerLng = '';

    if (space.geoPolygon && space.geoPolygon.length > 0) {
      const lats = space.geoPolygon.map(p => p[0]);
      const lngs = space.geoPolygon.map(p => p[1]);
      centerLat = ((Math.min(...lats) + Math.max(...lats)) / 2).toFixed(6);
      centerLng = ((Math.min(...lngs) + Math.max(...lngs)) / 2).toFixed(6);
    }

    return [
      space.id,
      space.status,
      space.confidence,
      space.vehicleCount || 0,
      space.areaSqMeters || 0,
      space.estimatedCapacity || 1,
      centerLat,
      centerLng
    ].join(',');
  });

  return [headers.join(','), ...rows].join('\n');
};

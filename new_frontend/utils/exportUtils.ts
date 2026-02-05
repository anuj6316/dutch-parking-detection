import { Space } from '../types';

/**
 * Helper to escape CSV fields. 
 * Wraps in quotes if it contains a comma, quote, or newline.
 */
const escapeCsvField = (field: string | number | undefined | null): string => {
  if (field === undefined || field === null) return '';
  const str = String(field);
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
};

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
      
      // Prepare OBB corners for properties (keep as [lat, lng])
      const obbCorners = space.geoObbCorners || [];

      return {
        type: 'Feature',
        properties: {
          id: space.id,
          status: space.status,
          confidence: space.confidence,
          vehicleCount: space.vehicleCount || 0,
          areaSqMeters: space.areaSqMeters || 0,
          estimatedCapacity: space.estimatedCapacity || 1,
          tileIndex: space.tileIndex,
          googleMapsLink: space.googleMapsLink,
          geoObbCorners: obbCorners
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
    'Center Longitude',
    'Google Maps Link',
    'Corner1_Lat', 'Corner1_Lng',
    'Corner2_Lat', 'Corner2_Lng',
    'Corner3_Lat', 'Corner3_Lng',
    'Corner4_Lat', 'Corner4_Lng'
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

    // Extract corners (pad with empty strings if missing)
    const corners = space.geoObbCorners || [];
    const cornerFields = [];
    for (let i = 0; i < 4; i++) {
        if (i < corners.length) {
            cornerFields.push(corners[i][0]); // Lat
            cornerFields.push(corners[i][1]); // Lng
        } else {
            cornerFields.push('');
            cornerFields.push('');
        }
    }

    return [
      escapeCsvField(space.id),
      escapeCsvField(space.status),
      escapeCsvField(space.confidence),
      escapeCsvField(space.vehicleCount || 0),
      escapeCsvField(space.areaSqMeters || 0),
      escapeCsvField(space.estimatedCapacity || 1),
      escapeCsvField(centerLat),
      escapeCsvField(centerLng),
      escapeCsvField(space.googleMapsLink || ''),
      ...cornerFields.map(escapeCsvField)
    ].join(',');
  });

  return [headers.join(','), ...rows].join('\n');
};

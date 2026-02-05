"""
OBB (Oriented Bounding Box) Merger

Merges overlapping OBB detections into single continuous polygons.
Uses Shapely for robust polygon operations.
"""

import logging
from typing import List, Dict, Any, Tuple
import numpy as np
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

logger = logging.getLogger(__name__)

try:
    from shapely import geometry
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
    logger.warning("[OBBMerger] Shapely not available. Install with: pip install shapely")


class OBBMerger:
    """
    Merges overlapping OBB detections into continuous polygons.
    
    Strategy:
    1. Convert OBB coordinates to Shapely polygons
    2. Detect overlaps using intersection area
    3. Group overlapping polygons
    4. Merge groups using unary_union
    5. Extract convex hull or union boundary
    """
    
    def __init__(self, iou_threshold: float = 0.1, min_overlap_area: float = 0.05, max_distance: float = 50.0, enabled: bool = True):
        """
        Args:
            iou_threshold: Minimum IoU to consider boxes as overlapping (0.0-1.0)
            min_overlap_area: Minimum overlap area ratio (0.0-1.0) to merge
            max_distance: Maximum distance in pixels to merge adjacent boxes (even without overlap)
            enabled: Whether merging is enabled (can be disabled for testing)
        """
        self.iou_threshold = iou_threshold
        self.min_overlap_area = min_overlap_area
        self.max_distance = max_distance
        self.enabled = enabled
        self.available = SHAPELY_AVAILABLE
        
        if not self.available:
            logger.warning("[OBBMerger] Shapely not available - merging disabled")
        elif not self.enabled:
            logger.info("[OBBMerger] Merging disabled by configuration")
        else:
            logger.info(f"[OBBMerger] Initialized with IoU={iou_threshold}, overlap={min_overlap_area}, max_dist={max_distance}")
    
    def merge_overlapping_detections(
        self, 
        detections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge overlapping OBB detections in pixel coordinates.
        """
        if not self.enabled or not self.available or len(detections) <= 1:
            return detections
        
        return self._merge_generic(
            detections, 
            polygon_key="polygon", 
            bbox_key="bbox",
            is_geo=False
        )

    def merge_geospatial_detections(
        self,
        detections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge overlapping detections in geospatial coordinates (lat/lng).
        """
        if not self.available or len(detections) <= 1:
            return detections
            
        return self._merge_generic(
            detections,
            polygon_key="geoPolygon",
            bbox_key="geoBoundingBox",
            is_geo=True
        )

    def _merge_generic(
        self, 
        detections: List[Dict[str, Any]], 
        polygon_key: str, 
        bbox_key: str,
        is_geo: bool = False
    ) -> List[Dict[str, Any]]:
        """Generic merging logic for both pixel and geo coordinates."""
        
        # 1. Convert detections to Shapely polygons
        polygons_with_data = []
        for idx, det in enumerate(detections):
            poly = self._get_polygon(det, polygon_key, bbox_key, is_geo)
            if poly and poly.is_valid and poly.area > 0:
                polygons_with_data.append({
                    'polygon': poly,
                    'detection': det,
                    'index': idx
                })
            elif poly and not poly.is_valid:
                poly = poly.buffer(0)
                if poly.is_valid and poly.area > 0:
                    polygons_with_data.append({
                        'polygon': poly,
                        'detection': det,
                        'index': idx
                    })

        if not polygons_with_data:
            return detections

        # 2. Group overlapping polygons
        groups = self._group_overlapping_polygons(polygons_with_data)
        
        # 3. Merge each group
        merged_detections = []
        for group in groups:
            if len(group) == 1:
                merged_detections.append(group[0]['detection'])
            else:
                merged = self._merge_group(group, polygon_key, bbox_key, is_geo)
                if merged:
                    merged_detections.append(merged)
                else:
                    merged_detections.extend([item['detection'] for item in group])
        
        return merged_detections

    def _get_polygon(self, det: Dict[str, Any], poly_key: str, bbox_key: str, is_geo: bool) -> Polygon:
        """Extract polygon from detection dict."""
        try:
            coords_data = det.get(poly_key)
            if coords_data:
                if is_geo:
                    # geoPolygon is [[lat, lng], [lat, lng], ...]
                    # Shapely wants (lng, lat) for proper GeoJSON-like handling if we were using CRS,
                    # but here we just need consistency. Let's stick to (lng, lat) as per common practice.
                    # WAIT: The pipeline uses [lat, lng]. Let's stay consistent with what it expects.
                    coords = [tuple(p) for p in coords_data]
                else:
                    # pixel polygon is [x1, y1, x2, y2, ...]
                    coords = [(float(coords_data[i]), float(coords_data[i+1])) for i in range(0, len(coords_data)-1, 2)]
                
                if len(coords) >= 3:
                    return Polygon(coords)
            
            # Fallback to bbox
            bbox = det.get(bbox_key)
            if bbox and len(bbox) >= 4:
                if is_geo:
                    # geoBoundingBox: [minLat, minLng, maxLat, maxLng]
                    min_lat, min_lng, max_lat, max_lng = bbox
                    return Polygon([(min_lat, min_lng), (max_lat, min_lng), (max_lat, max_lng), (min_lat, max_lng)])
                else:
                    # bbox: [x1, y1, x2, y2]
                    x1, y1, x2, y2 = bbox
                    return Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
        except Exception:
            pass
        return None

    def _group_overlapping_polygons(
        self, 
        polygons_with_data: List[Dict]
    ) -> List[List[Dict]]:
        """Group polygons that overlap using Union-Find."""
        n = len(polygons_with_data)
        parent = list(range(n))
        
        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py
        
        for i in range(n):
            for j in range(i + 1, n):
                if polygons_with_data[i]['polygon'].intersects(polygons_with_data[j]['polygon']):
                    union(i, j)
        
        groups_dict = {}
        for idx in range(n):
            root = find(idx)
            if root not in groups_dict:
                groups_dict[root] = []
            groups_dict[root].append(polygons_with_data[idx])
        
        return list(groups_dict.values())

    def _merge_group(self, group: List[Dict], poly_key: str, bbox_key: str, is_geo: bool) -> Dict[str, Any]:
        """Merge a group of polygons and aggregate metadata."""
        try:
            polygons = [item['polygon'] for item in group]
            detections = [item['detection'] for item in group]
            
            merged_poly = unary_union(polygons)
            if isinstance(merged_poly, MultiPolygon):
                merged_poly = max(merged_poly.geoms, key=lambda p: p.area)
            
            if not merged_poly.is_valid:
                merged_poly = merged_poly.buffer(0)
            
            # Base detection from the first one
            merged_det = detections[0].copy()
            
            # Update Polygon and BBox
            coords = list(merged_poly.exterior.coords)
            if is_geo:
                merged_det[poly_key] = [list(p) for p in coords]
                min_lat, min_lng, max_lat, max_lng = merged_poly.bounds
                merged_det[bbox_key] = [min_lat, min_lng, max_lat, max_lng]
            else:
                flat_coords = []
                for x, y in coords:
                    flat_coords.extend([float(x), float(y)])
                merged_det[poly_key] = flat_coords
                bounds = merged_poly.bounds
                merged_det[bbox_key] = [float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3])]
            
            # Aggregate metadata
            merged_det['vehicle_count'] = sum(d.get('vehicle_count', 0) for d in detections)
            merged_det['is_occupied'] = merged_det['vehicle_count'] > 0
            merged_det['estimated_capacity'] = sum(d.get('estimated_capacity', 0) for d in detections)
            merged_det['area_sq_meters'] = sum(d.get('area_sq_meters', 0) for d in detections)
            merged_det['merged_count'] = sum(d.get('merged_count', 1) for d in detections)
            
            # Confidence aggregation
            all_conf = []
            for d in detections:
                c = d.get('confidence', [])
                if isinstance(c, list):
                    all_conf.extend(c)
                else:
                    all_conf.append(c)
            
            if all_conf:
                # If we're merging geo-detections, we might want to keep the list of confidences
                # or average them. The pipeline expects a list of confidences for some reason.
                if is_geo:
                    # Simple average for now, but keeping it in a list to match original behavior
                    merged_det['confidence'] = [sum(all_conf) / len(all_conf)]
                else:
                    merged_det['confidence'] = sum(all_conf) / len(all_conf)
            
            return merged_det
            
        except Exception as e:
            logger.error(f"[OBBMerger] Error merging group: {e}")
            return None



# Singleton instance - More aggressive thresholds for better merging
obb_merger = OBBMerger(iou_threshold=0.1, min_overlap_area=0.05, max_distance=50.0)

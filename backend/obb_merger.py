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
        Merge overlapping OBB detections into single polygons.
        
        Args:
            detections: List of detection dicts with 'bbox' and/or 'polygon' keys
            
        Returns:
            List of merged detections with combined polygons
        """
        if not self.enabled or not self.available or len(detections) == 0:
            return detections
        
        if len(detections) == 1:
            return detections
        
        logger.info(f"[OBBMerger] Processing {len(detections)} detections for merging (IoU={self.iou_threshold}, overlap={self.min_overlap_area}, max_dist={self.max_distance})")
        
        # Convert detections to Shapely polygons
        polygons_with_data = []
        invalid_count = 0
        for idx, det in enumerate(detections):
            poly = self._detection_to_polygon(det)
            if poly:
                # Try to fix invalid geometries
                if not poly.is_valid:
                    poly = poly.buffer(0)  # Fix self-intersections
                
                if poly.is_valid and poly.area > 0:
                    polygons_with_data.append({
                        'polygon': poly,
                        'detection': det,
                        'index': idx
                    })
                else:
                    invalid_count += 1
                    logger.debug(f"[OBBMerger] Invalid or zero-area polygon at index {idx}")
            else:
                invalid_count += 1
                logger.debug(f"[OBBMerger] Could not convert detection {idx} to polygon")
        
        if invalid_count > 0:
            logger.warning(f"[OBBMerger] Skipped {invalid_count} invalid detections out of {len(detections)}")
        
        if len(polygons_with_data) == 0:
            logger.warning("[OBBMerger] No valid polygons to merge")
            return detections
        
        # Group overlapping polygons
        groups = self._group_overlapping_polygons(polygons_with_data)
        logger.info(f"[OBBMerger] Found {len(groups)} groups (from {len(polygons_with_data)} detections)")
        
        # Merge each group
        merged_detections = []
        for group_idx, group in enumerate(groups):
            if len(group) == 1:
                # Single detection, no merging needed
                merged_detections.append(group[0]['detection'])
            else:
                # Merge multiple detections
                merged = self._merge_group(group)
                if merged:
                    merged_detections.append(merged)
                    logger.info(f"[OBBMerger] Group {group_idx}: Merged {len(group)} detections")
        
        reduction = len(detections) - len(merged_detections)
        if reduction > 0:
            logger.info(f"[OBBMerger] Successfully merged: {len(detections)} → {len(merged_detections)} polygons (reduced by {reduction})")
        else:
            logger.info(f"[OBBMerger] No merging occurred: {len(detections)} detections remain")
        return merged_detections
    
    def _detection_to_polygon(self, det: Dict[str, Any]) -> Polygon:
        """Convert detection dict to Shapely Polygon."""
        try:
            if "polygon" in det and det["polygon"]:
                # OBB polygon: [x1, y1, x2, y2, x3, y3, x4, y4, ...]
                points = det["polygon"]
                if len(points) >= 6:  # Need at least 3 points (6 coordinates)
                    coords = [(float(points[i]), float(points[i+1])) for i in range(0, len(points)-1, 2)]
                    # Ensure polygon is closed
                    if len(coords) > 0 and coords[0] != coords[-1]:
                        coords.append(coords[0])
                    if len(coords) >= 3:
                        return Polygon(coords)
            elif "bbox" in det and det["bbox"]:
                # Standard bounding box: [x1, y1, x2, y2]
                bbox = det["bbox"]
                if len(bbox) >= 4:
                    x1, y1, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
                    return Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)])
        except Exception as e:
            logger.debug(f"[OBBMerger] Error converting detection to polygon: {e}")
        
        return None
    
    def _group_overlapping_polygons(
        self, 
        polygons_with_data: List[Dict]
    ) -> List[List[Dict]]:
        """
        Group polygons that overlap with each other.
        Uses union-find approach to find connected components.
        """
        n = len(polygons_with_data)
        if n == 0:
            return []
        
        # Union-Find data structure
        parent = list(range(n))
        
        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py
        
        # Check all pairs for overlap
        overlaps_found = 0
        for i in range(n):
            for j in range(i + 1, n):
                poly1 = polygons_with_data[i]['polygon']
                poly2 = polygons_with_data[j]['polygon']
                
                if self._polygons_overlap(poly1, poly2):
                    union(i, j)
                    overlaps_found += 1
        
        logger.debug(f"[OBBMerger] Found {overlaps_found} overlapping pairs out of {n * (n-1) // 2} total pairs")
        
        # Group by root parent
        groups_dict = {}
        for idx in range(n):
            root = find(idx)
            if root not in groups_dict:
                groups_dict[root] = []
            groups_dict[root].append(polygons_with_data[idx])
        
        return list(groups_dict.values())
    
    def _polygons_overlap(self, poly1: Polygon, poly2: Polygon) -> bool:
        """Check if two polygons should be merged based on overlap or proximity."""
        # Check if polygons intersect
        if poly1.intersects(poly2):
            # Calculate IoU
            intersection = poly1.intersection(poly2)
            if not intersection.is_empty:
                intersection_area = intersection.area
                union_area = poly1.union(poly2).area
                
                if union_area > 0:
                    iou = intersection_area / union_area
                    
                    # Also check if overlap area is significant relative to smaller polygon
                    min_area = min(poly1.area, poly2.area)
                    if min_area > 0:
                        overlap_ratio = intersection_area / min_area
                        
                        # Merge if IoU > threshold OR overlap area > min_overlap_area of smaller polygon
                        if iou >= self.iou_threshold or overlap_ratio >= self.min_overlap_area:
                            return True
        
        # Check distance for adjacent boxes (even without overlap)
        # Calculate minimum distance between polygons
        distance = poly1.distance(poly2)
        
        if distance <= self.max_distance:
            # For very close boxes, merge them. The area ratio check was too strict
            # and prevented merging of adjacent fragments of different sizes.
            return True
        
        return False
    
    def _merge_group(self, group: List[Dict]) -> Dict[str, Any]:
        """
        Merge a group of overlapping detections into a single detection.
        
        Strategy:
        1. Union all polygons
        2. Take convex hull or union boundary
        3. Aggregate metadata (confidence, vehicle counts, etc.)
        """
        if len(group) == 0:
            return None
        
        polygons = [item['polygon'] for item in group]
        detections = [item['detection'] for item in group]
        
        # Union all polygons
        try:
            if len(polygons) == 1:
                merged_poly = polygons[0]
            else:
                # Use unary_union for efficient merging
                merged_poly = unary_union(polygons)
            
            # If result is MultiPolygon, take the largest component
            if isinstance(merged_poly, MultiPolygon):
                merged_poly = max(merged_poly.geoms, key=lambda p: p.area)
            
            # Optionally use convex hull for smoother boundaries
            # merged_poly = merged_poly.convex_hull
            
            # Extract coordinates
            if not merged_poly.is_valid:
                # Try to fix invalid geometry
                merged_poly = merged_poly.buffer(0)
            
            # Get exterior coordinates
            coords = list(merged_poly.exterior.coords)
            # Remove duplicate closing point (Shapely includes it, but we'll add it back if needed)
            if len(coords) > 0 and coords[0] == coords[-1]:
                coords = coords[:-1]
            
            # Flatten to [x1, y1, x2, y2, ...] format
            # Ensure we have at least 3 points (6 coordinates)
            if len(coords) < 3:
                logger.warning(f"[OBBMerger] Merged polygon has only {len(coords)} points, using original")
                return detections[0]
            
            polygon_flat = []
            for x, y in coords:
                polygon_flat.extend([float(x), float(y)])
            
            logger.debug(f"[OBBMerger] Merged polygon has {len(coords)} points ({len(polygon_flat)} coordinates)")
            
            # Aggregate metadata from all detections
            confidences = [d.get('confidence', 0.0) for d in detections]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Use the first detection as base, update with merged data
            merged_det = detections[0].copy()
            merged_det['polygon'] = polygon_flat
            merged_det['bbox'] = self._polygon_to_bbox(merged_poly)
            merged_det['confidence'] = avg_confidence
            merged_det['merged_count'] = len(group)
            # Note: vehicle_count and is_occupied will be calculated later in the pipeline
            
            # Recalculate capacity based on merged polygon area
            if 'area_sq_meters' in merged_det:
                # Estimate area from polygon
                area_pixels = merged_poly.area
                # Assuming 5cm per pixel (PDOK resolution)
                area_sq_meters = area_pixels * (0.05 ** 2)
                merged_det['area_sq_meters'] = round(area_sq_meters, 2)
            
            return merged_det
            
        except Exception as e:
            logger.error(f"[OBBMerger] Error merging group: {e}")
            # Return first detection as fallback
            return detections[0]
    
    def _polygon_to_bbox(self, poly: Polygon) -> List[float]:
        """Convert Shapely polygon to axis-aligned bounding box."""
        bounds = poly.bounds  # (minx, miny, maxx, maxy)
        return [float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3])]


# Singleton instance - More aggressive thresholds for better merging
obb_merger = OBBMerger(iou_threshold=0.1, min_overlap_area=0.05, max_distance=50.0)

import logging
from typing import List, Dict, Any
from PIL import Image
import base64
import io
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

from yolo_detector import YOLODetector
from mask_generator import MaskGenerator
from vehicle_counter import vehicle_counter
from capacity_estimator import estimate_parking_capacity
from obb_merger import obb_merger

logger = logging.getLogger(__name__)

CONFIG = {
    "tile_size": 256,
}


class PipelineOrchestrator:
    def __init__(self):
        self.yolo_detector = YOLODetector()
        self.mask_generator = MaskGenerator(fill_color="#FF0000", alpha=0.4)
        logger.info("[Pipeline] Initialized")

    def _merge_geo_polygons(self, detections: List[Dict]) -> List[Dict]:
        if len(detections) <= 1:
            return detections

        logger.info(f"[GlobalMerge] Starting global merge on {len(detections)} detections")

        # 1. Convert geoPolygons to shapely Polygons
        polygons_with_data = []
        for idx, det in enumerate(detections):
            geo_poly_coords = det.get("geoPolygon")
            if geo_poly_coords and len(geo_poly_coords) >= 3:
                try:
                    # Shapely wants list of tuples, geoPolygon is list of lists
                    coords = [tuple(p) for p in geo_poly_coords]
                    poly = Polygon(coords)
                    if not poly.is_valid:
                        poly = poly.buffer(0)  # Fix self-intersections
                    
                    if poly.is_valid and not poly.is_empty:
                        polygons_with_data.append({'polygon': poly, 'detection': det, 'index': idx})
                except Exception as e:
                    logger.warning(f"[GlobalMerge] Could not create polygon for detection {idx}: {e}")

        # 2. Group overlapping polygons (Union-Find)
        n = len(polygons_with_data)
        if n == 0:
            return detections
            
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
                # Using a simple intersection check. This is sufficient for merging
                # across tiles and avoids complex geodetic distance/area calculations.
                if polygons_with_data[i]['polygon'].intersects(polygons_with_data[j]['polygon']):
                    union(i, j)

        # 3. Group by root parent
        groups_dict = {}
        for idx in range(n):
            root = find(idx)
            if root not in groups_dict:
                groups_dict[root] = []
            groups_dict[root].append(polygons_with_data[idx])
        groups = list(groups_dict.values())
        
        logger.info(f"[GlobalMerge] Found {len(groups)} groups from {n} valid polygons")

        # 4. Merge each group and create new detections
        merged_detections = []
        for group in groups:
            if len(group) == 1:
                merged_detections.append(group[0]['detection'])
                continue

            # Merge polygons
            try:
                polygons_in_group = [item['polygon'] for item in group]
                merged_poly = unary_union(polygons_in_group)

                if isinstance(merged_poly, MultiPolygon):
                    merged_poly = max(merged_poly.geoms, key=lambda p: p.area)
                
                # Create a new aggregated detection object
                original_dets = [item['detection'] for item in group]
                new_det = original_dets[0].copy() # Start with the first one
                
                # Update polygon
                new_geo_polygon = [list(p) for p in merged_poly.exterior.coords]
                new_det['geoPolygon'] = new_geo_polygon
                
                # Update bbox
                min_lng, min_lat, max_lng, max_lat = merged_poly.bounds
                new_det['geoBoundingBox'] = [min_lat, min_lng, max_lat, max_lng]
                
                # Aggregate other fields
                new_det['vehicle_count'] = sum(d.get('vehicle_count', 0) for d in original_dets)
                new_det['is_occupied'] = new_det['vehicle_count'] > 0
                new_det['estimated_capacity'] = sum(d.get('estimated_capacity', 0) for d in original_dets)
                new_det['area_sq_meters'] = sum(d.get('area_sq_meters', 0) for d in original_dets)
                new_det['merged_count'] = sum(d.get('merged_count', 1) for d in original_dets)
                
                # confidences = [c for d in original_dets for c in d.get('confidence', []) if c is not None]
                # if confidences:
                #     new_det['confidence'] = [sum(confidences) / len(confidences)]
                # else:
                #     new_det['confidence'] = [0]
                confidences = [c for d in original_dets for c in d.get('confidence', []) if c is not None]

                if confidences:
                    c_min = min(confidences)
                    c_max = max(confidences)

                    # avoid divide-by-zero if all values are same
                    if c_max == c_min:
                        norm_confidences = [0.85 for _ in confidences]  # midpoint of 0.8–0.9
                    else:
                        norm_confidences = [
                            0.8 + (c - c_min) * (0.9 - 0.8) / (c_max - c_min)
                            for c in confidences
                        ]
                else:
                    norm_confidences = []


                merged_detections.append(new_det)
            except Exception as e:
                logger.error(f"[GlobalMerge] Error merging group: {e}")
                # Fallback to returning original detections in group
                merged_detections.extend([item['detection'] for item in group])

        return merged_detections

    async def run(self, tiles: List[Dict], confidence: float = 0.25):
        """Run the complete detection pipeline and stream updates."""
        all_detections = []
        all_masks = []
        failed_tiles = []
        
        total_tiles = len(tiles)
        logger.info(f"[Pipeline] Starting with {total_tiles} tiles")
        
        yield {"type": "log", "message": f"[Step 1/5] Initialized analysis for {total_tiles} tiles"}
        yield {"type": "progress", "value": 0}

        for idx, tile in enumerate(tiles):
            try:
                image = self._decode_image(tile["image_base64"])
                tile_idx = tile["tile_index"]
                progress = int(((idx + 1) / total_tiles) * 80) # Use 80% for per-tile processing

                yield {"type": "log", "message": f"[Tile {idx+1}/{total_tiles}] Starting YOLO detection..."}

                # YOLO Detection
                detections = self.yolo_detector.detect_parking_spaces(image, confidence)
                yield {"type": "log", "message": f"[Tile {idx+1}] YOLO found {len(detections)} parking spaces"}
                
                # Merge overlapping OBB detections
                if len(detections) > 0:
                    detections_before_merge = len(detections)
                    detections = obb_merger.merge_overlapping_detections(detections)
                    if len(detections) < detections_before_merge:
                        yield {"type": "log", "message": f"[Tile {idx+1}] Merged overlapping detections: {detections_before_merge} → {len(detections)}"}

                # STEP 3: Generate Detection Masks
                mask = self.mask_generator.generate_mask(image, detections)
                mask_b64 = self._encode_image(mask)
                all_masks.append({"tile_index": tile_idx, "mask": mask_b64})
                
                # STEP 4: Vehicle Detection
                tile_detections = []
                total_vehicles = 0

                for det_idx, det in enumerate(detections):
                    cropped = self._crop_from_bbox(image, det["bbox"])
                    vehicle_result = vehicle_counter.count_vehicles(cropped, confidence_threshold=0.5)
                    vehicle_count = vehicle_result["count"]
                    total_vehicles += vehicle_count

                    # Convert pixel coordinates to Geo coordinates
                    tile_bounds = tile["bounds"]
                    img_w, img_h = image.size

                    # Compute GeoPolygon
                    geo_polygon = []
                    if "polygon" in det and det["polygon"]:
                        poly_points = det["polygon"]
                        for i in range(0, len(poly_points) - 1, 2):
                            px, py = max(0, min(img_w - 1, float(poly_points[i]))), max(0, min(img_h - 1, float(poly_points[i+1])))
                            lat, lng = self._pixel_to_geo(px, py, img_w, img_h, tile_bounds)
                            geo_polygon.append([lat, lng])
                        if len(geo_polygon) > 0 and geo_polygon[0] != geo_polygon[-1]:
                            geo_polygon.append([geo_polygon[0][0], geo_polygon[0][1]])
                    
                    lats, lngs = [p[0] for p in geo_polygon], [p[1] for p in geo_polygon]
                    geo_bbox = [min(lats), min(lngs), max(lats), max(lngs)] if geo_polygon else [0,0,0,0]

                    obb_coords = det["polygon"] if "polygon" in det and det["polygon"] else self._bbox_to_obb(det["bbox"])
                    capacity = estimate_parking_capacity(obb_coords, spot_type="standard")

                    tile_detections.append({
                        "tile_index": tile_idx,
                        "confidence": [det["confidence"]],
                        "vehicle_count": vehicle_count,
                        "is_occupied": vehicle_count > 0,
                        "geoBoundingBox": geo_bbox,
                        "geoPolygon": geo_polygon,
                        "area_sq_meters": capacity["area_sq_meters"],
                        "estimated_capacity": capacity["estimated_capacity"],
                        "dimensions_meters": capacity["dimensions_meters"],
                        "cropped_image": self._encode_image(cropped),
                        "cropped_overlay": vehicle_result.get("overlay_image"),
                    })

                all_detections.extend(tile_detections)
                yield {"type": "log", "message": f"[Tile {idx+1}] Complete: {len(tile_detections)} spaces, {total_vehicles} vehicles"}
                yield {"type": "progress", "value": progress}

            except Exception as e:
                logger.error(f"[Tile {idx}] Failed: {e}")
                yield {"type": "log", "message": f"[Error] Tile {idx+1} failed: {str(e)}"}
                failed_tiles.append(tile_idx)

        # STEP 5: Global Merge
        yield {"type": "log", "message": "[Step 5/5] Performing Global Geospatial Merge..."}
        detections_before_global_merge = len(all_detections)
        all_detections = self._merge_geo_polygons(all_detections)
        reduction = detections_before_global_merge - len(all_detections)
        
        if reduction > 0:
            yield {"type": "log", "message": f"[Pipeline] Global merge complete. Reduced detections by {reduction}."}

        yield {"type": "progress", "value": 100}
        
        # Final result structure
        yield {
            "type": "final_result",
            "data": {
                "detections": all_detections,
                "detection_masks": all_masks,
                "total_spaces": len(all_detections),
                "total_vehicles_detected": sum(d.get("vehicle_count", 0) for d in all_detections),
                "failed_tiles": failed_tiles
            }
        }


    def _pixel_to_geo(
        self, x: float, y: float, width: int, height: int, bounds: Dict[str, float]
    ) -> tuple:
        """Convert pixel coordinates to (lat, lng) using Mercator projection math."""
        import math

        def lat_to_merc(lat):
            return math.log(math.tan(math.radians(lat) / 2 + math.pi / 4))

        def merc_to_lat(merc):
            return math.degrees(2 * math.atan(math.exp(merc)) - math.pi / 2)

        min_lat = bounds["minLat"]
        max_lat = bounds["maxLat"]
        min_lng = bounds["minLng"]
        max_lng = bounds["maxLng"]

        # Longitude is linear
        lng = min_lng + (x / width) * (max_lng - min_lng)

        # Latitude is non-linear (Mercator)
        merc_max = lat_to_merc(max_lat)
        merc_min = lat_to_merc(min_lat)

        # Invert: y=0 is top (merc_max), y=height is bottom (merc_min)
        merc_y = merc_max - (y / height) * (merc_max - merc_min)
        lat = merc_to_lat(merc_y)

        return lat, lng

    def _decode_image(self, base64_string: str) -> Image.Image:
        header, data = base64_string.split(",", 1)
        img_data = base64.b64decode(data)
        return Image.open(io.BytesIO(img_data))

    def _encode_image(self, image: Image.Image) -> str:
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()

    def _crop_from_bbox(self, image: Image.Image, bbox: List[float]) -> Image.Image:
        x1, y1, x2, y2 = [float(b) for b in bbox]
        return image.crop((x1, y1, x2, y2))

    def _bbox_to_obb(self, bbox: List[float]) -> List[float]:
        x1, y1, x2, y2 = [float(b) for b in bbox]
        return [x1, y1, x2, y1, x2, y2, x1, y2]

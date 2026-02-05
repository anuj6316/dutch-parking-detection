import logging
import asyncio
from typing import List, Dict, Any

from yolo_detector import YOLODetector
from mask_generator import MaskGenerator
from vehicle_counter import vehicle_counter
from capacity_estimator import estimate_parking_capacity
from obb_merger import obb_merger
from geo_utils import pixel_to_geo
from crop_utils import crop_obb_region
from image_utils import decode_image, encode_image, crop_from_bbox, bbox_to_obb

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(self):
        self.yolo_detector = YOLODetector()
        self.mask_generator = MaskGenerator(fill_color="#FF0000", alpha=0.4)
        logger.info("[Pipeline] Initialized")
    
    async def run(self, tiles: List[Dict], confidence: float = 0.25):
        # sourcery skip: low-code-quality
        """Run the complete detection pipeline and stream updates."""
        all_detections = []
        all_masks = []
        failed_tiles = []

        total_tiles = len(tiles)
        logger.info(f"[Pipeline] Starting with {total_tiles} tiles")

        yield {"type": "log", "message": f"[Step 1/5] Initialized analysis for {total_tiles} tiles"}
        yield {"type": "progress", "value": 0}

        loop = asyncio.get_running_loop()
        
        for idx, tile in enumerate(tiles):
            # Check for cancellation at the start of each tile
            await asyncio.sleep(0)
            
            try:
                image = decode_image(tile["image_base64"])
                tile_idx = tile["tile_index"]
                progress = int(((idx + 1) / total_tiles) * 80) # Use 80% for per-tile processing

                yield {"type": "log", "message": f"[Tile {idx+1}/{total_tiles}] Starting YOLO detection..."}

                # YOLO Detection (Offloaded to executor)
                detections = await loop.run_in_executor(None, self.yolo_detector.detect_parking_spaces, image, confidence)
                yield {"type": "log", "message": f"[Tile {idx+1}] YOLO found {len(detections)} parking spaces"}

                # Merge overlapping OBB detections
                if len(detections) > 0:
                    detections_before_merge = len(detections)
                    detections = obb_merger.merge_overlapping_detections(detections)
                    if len(detections) < detections_before_merge:
                        yield {"type": "log", "message": f"[Tile {idx+1}] Merged overlapping detections: {detections_before_merge} → {len(detections)}"}

                # STEP 3: Generate Detection Masks
                mask = self.mask_generator.generate_mask(image, detections)
                mask_b64 = encode_image(mask)
                all_masks.append({"tile_index": tile_idx, "mask": mask_b64})

                # STEP 4: Vehicle Detection (Batch Processing)
                tile_detections = []
                total_vehicles = 0
                
                # Prepare batch inputs
                batch_crops = []
                batch_indices = []
                
                for det_idx, det in enumerate(detections):
                    # Use OBB crop if polygon is available, otherwise fallback to bbox crop
                    if "polygon" in det and det["polygon"] and len(det["polygon"]) == 8:
                        cropped = crop_obb_region(image, det["polygon"])
                    else:
                        cropped = crop_from_bbox(image, det["bbox"])
                    
                    batch_crops.append(cropped)
                    batch_indices.append(det_idx)

                # Process batch if there are detections
                batch_results = []
                if batch_crops:
                    # Vehicle Counting (Offloaded to executor for thread safety, though batching happens inside)
                    # Note: We pass the list of images to the batch method
                    batch_results = await loop.run_in_executor(
                        None, 
                        vehicle_counter.count_vehicles_batch, 
                        batch_crops, 
                        0.5
                    )
                
                # Map results back to detections
                for i, det_idx in enumerate(batch_indices):
                    # Check for cancellation
                    if i % 10 == 0:
                        await asyncio.sleep(0)

                    det = detections[det_idx]
                    vehicle_result = batch_results[i]
                    
                    vehicle_count = vehicle_result["count"]
                    total_vehicles += vehicle_count

                    # Convert pixel coordinates to Geo coordinates
                    tile_bounds = tile["bounds"]
                    img_w, img_h = image.size

                    # Compute GeoPolygon
                    geo_polygon = []
                    if "polygon" in det and det["polygon"]:
                        poly_points = det["polygon"]
                        for k in range(0, len(poly_points) - 1, 2):
                            px, py = max(0, min(img_w - 1, float(poly_points[k]))), max(0, min(img_h - 1, float(poly_points[k+1])))
                            lat, lng = pixel_to_geo(px, py, img_w, img_h, tile_bounds)
                            geo_polygon.append([lat, lng])
                        if geo_polygon and geo_polygon[0] != geo_polygon[-1]:
                            geo_polygon.append([geo_polygon[0][0], geo_polygon[0][1]])

                    lats, lngs = [p[0] for p in geo_polygon], [p[1] for p in geo_polygon]
                    geo_bbox = [min(lats), min(lngs), max(lats), max(lngs)] if geo_polygon else [0,0,0,0]
                    
                    # Calculate center for Google Maps link
                    center_lat = sum(lats) / len(lats) if lats else 0
                    center_lng = sum(lngs) / len(lngs) if lngs else 0
                    google_maps_link = f"https://www.google.com/maps/search/?api=1&query={center_lat},{center_lng}"
                    
                    # Calculate OBB corners (Lat/Lng) for export
                    if geo_polygon and len(geo_polygon) >= 4:
                        geo_obb_corners = geo_polygon[:4]
                    else:
                        # Fallback to bbox corners
                        min_lat, min_lng, max_lat, max_lng = geo_bbox
                        geo_obb_corners = [
                            [min_lat, min_lng], [max_lat, min_lng],
                            [max_lat, max_lng], [min_lat, max_lng]
                        ]

                    obb_coords = det["polygon"] if "polygon" in det and det["polygon"] else bbox_to_obb(det["bbox"])
                    capacity = estimate_parking_capacity(obb_coords, spot_type="standard")

                    tile_detections.append({
                        "tile_index": tile_idx,
                        "confidence": [det["confidence"]],
                        "vehicle_count": vehicle_count,
                        "is_occupied": vehicle_count > 0,
                        "geoBoundingBox": geo_bbox,
                        "geoPolygon": geo_polygon,
                        "geo_obb_corners": geo_obb_corners,
                        "google_maps_link": google_maps_link,
                        "area_sq_meters": capacity["area_sq_meters"],
                        "estimated_capacity": capacity["estimated_capacity"],
                        "dimensions_meters": capacity["dimensions_meters"],
                        "cropped_image": encode_image(batch_crops[i]),
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
        
        # Use the updated OBBMerger for geospatial merging
        all_detections = obb_merger.merge_geospatial_detections(all_detections)
        
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
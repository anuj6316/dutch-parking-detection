"""
Local Vehicle Counter using SAM3 (Segment Anything Model 3) for precise vehicle segmentation.

SAM3 Features:
- Promptable Concept Segmentation (PCS) with text prompts
- High accuracy instance segmentation
- Returns masks, bounding boxes, and confidence scores

Falls back to YOLOv8n if SAM3 is not available.
"""

import os
import io
import base64
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from PIL import Image, ImageDraw
import numpy as np
from config import settings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get HuggingFace token for gated models
HF_TOKEN = os.environ.get("HF_API_KEY") or os.environ.get("HF_TOKEN")

# Logging into the HF account
try:
    from huggingface_hub import login, whoami
    login(token=HF_TOKEN, add_to_git_credential=False)
    # logging.info("HuggingFace login successful")
    user = whoami()
    logging.info(f"Logged into HuggingFace as: {user['name']}")
except Exception as e:
    logging.exception(f"Error during HuggingFace login: {e}")

# Skip SAM3 loading for faster testing - set to True to enable
SKIP_SAM3_LOADING = settings.SKIP_SAM3_LOADING
logging.info(f"skip sam3 model--> {SKIP_SAM3_LOADING}")
    

# Check SAM3 availability (primary - most accurate)
SAM3_AVAILABLE = False
sam3_model = None
sam3_processor = None
# device = "gpu"

if not SKIP_SAM3_LOADING:
    logging.info(f"SKIP_SAM3_LOADING: {SKIP_SAM3_LOADING}")
    try:
        import torch
        from transformers import Sam3Processor, Sam3Model

        device = "cuda" if torch.cuda.is_available() else "cpu"
        # device = "cpu"
        logger.info(f"[VehicleCounter] Initializing SAM3 on device: {device}")

        sam3_model = Sam3Model.from_pretrained(
            "facebook/sam3", token=HF_TOKEN, torch_dtype=torch.float32
        ).to(device)
        sam3_processor = Sam3Processor.from_pretrained("facebook/sam3", token=HF_TOKEN)

        SAM3_AVAILABLE = True
        logger.info(f"[VehicleCounter] SAM3 loaded successfully on {device}")

    except ImportError as e:
        logger.error(
            f"[VehicleCounter] SAM3 not available (transformers needs update): {e}"
        )
    except Exception as e:
        logger.error(f"[VehicleCounter] SAM3 loading error: {e}")
        if "facebook/sam3" in str(e):
            logger.warning(
                "[VehicleCounter] Make sure you have accepted the license at https://huggingface.co/facebook/sam3"
            )
else:
    logger.info(
        "[VehicleCounter] SAM3 loading skipped (SKIP_SAM3_LOADING=True) - Using YOLO only"
    )

COLAB_PROXY_URL = os.environ.get("SAM3_COLAB_URL")
COLAB_AVAILABLE = False
if COLAB_PROXY_URL:
    try:
        import requests

        resp = requests.get(f"{COLAB_PROXY_URL.rstrip('/')}/health", timeout=5)
        if resp.status_code == 200:
            COLAB_AVAILABLE = True
            logger.info(
                f"[VehicleCounter] SAM3 Colab Proxy available at {COLAB_PROXY_URL}"
            )
    except:
        pass

YOLO_AVAILABLE = False
yolo_model = None

try:
    from ultralytics import YOLO

    YOLO_AVAILABLE = True
    logger.info("[VehicleCounter] Ultralytics YOLO available as fallback")
except ImportError:
    logger.warning("[VehicleCounter] Ultralytics YOLO not available")


class VehicleCounter:
    """
    Vehicle counter using SAM3 (Local or Proxy) for high-accuracy segmentation.

    Priority:
    1. Local SAM3 (if GPU)
    2. Colab Proxy (if available - fast)
    3. Local SAM3 (if CPU - slow)
    4. YOLO (fallback)
    """

    def __init__(self):
        self.sam3_model = sam3_model
        self.sam3_processor = sam3_processor
        self.yolo_model = None
        self.device = device if SAM3_AVAILABLE else "cpu"
        self.colab_url = COLAB_PROXY_URL

        # Vehicle-related text prompts for SAM3
        self.vehicle_prompts = ["car", "vehicle", "automobile"]

        # YOLO vehicle classes (fallback)
        self.vehicle_classes = {
            2: "car",
            3: "motorcycle",
            5: "bus",
            7: "truck",
            1: "bicycle",
        }

        self._init_fallback_models()

        if SAM3_AVAILABLE:
            logger.info("[VehicleCounter] SAM3 available locally")
        elif COLAB_AVAILABLE:
            logger.info(
                f"[VehicleCounter] SAM3 Colab Proxy available at {COLAB_PROXY_URL}"
            )
            logger.info(
                "[VehicleCounter] Using SAM3 via Colab Proxy (Source: Remote GPU)"
            )
        elif YOLO_AVAILABLE:
            logger.info("[VehicleCounter] Using YOLO fallback for vehicle detection")
        else:
            logger.warning("[VehicleCounter] Warning: No detection model available!")

    def _is_fully_visible(
        self, box: Dict, image_width: int, image_height: int, edge_margin: int = 5
    ) -> bool:
        """Check if a detected vehicle is fully visible (not cut off at edges)."""
        xmin = box.get("xmin", 0)
        ymin = box.get("ymin", 0)
        xmax = box.get("xmax", 0)
        ymax = box.get("ymax", 0)

        is_cut_off = (
            xmin <= edge_margin
            or ymin <= edge_margin
            or xmax >= (image_width - edge_margin)
            or ymax >= (image_height - edge_margin)
        )

        return not is_cut_off

    def _init_fallback_models(self):
        """Initialize fallback YOLO model if needed."""
        if not SAM3_AVAILABLE and not COLAB_AVAILABLE and YOLO_AVAILABLE:
            try:
                # Use environment variable or relative path for the fallback model
                fallback_model_path = os.getenv("YOLO_FALLBACK_MODEL", "../yolo26n.pt")
                logger.info(f"[VehicleCounter] Loading YOLO fallback from {fallback_model_path}...")
                self.yolo_model = YOLO(fallback_model_path)
                logger.info("[VehicleCounter] YOLO fallback loaded!")
            except Exception as e:
                logger.error(f"[VehicleCounter] Error loading YOLO fallback: {e}")

    def count_vehicles(
        self, image: Image.Image, confidence_threshold: float = 0.3, prompt: str = "car"
    ) -> Dict[str, Any]:
        """
        Count vehicles in a single image (Wrapper for batch processing).
        """
        results = self.count_vehicles_batch([image], confidence_threshold, prompt)
        return results[0] if results else {
            "count": 0,
            "detections": [],
            "source": "error",
            "error": "Batch processing returned empty",
        }

    def count_vehicles_batch(
        self, images: List[Image.Image], confidence_threshold: float = 0.3, prompt: str = "car"
    ) -> List[Dict[str, Any]]:
        """
        Count vehicles in a batch of images using SAM3 (Local/Proxy) or YOLO.
        """
        if not images:
            return []

        # 1. Try Colab Proxy (Not implemented for batch yet, fallback to loop or local)
        if COLAB_AVAILABLE and "cuda" not in self.device:
            # Fallback to sequential for proxy if batching isn't supported there
            return [self._count_with_colab_proxy(img, confidence_threshold, prompt) for img in images]

        # 2. Try Local SAM3
        if SAM3_AVAILABLE and self.sam3_model is not None:
            return self._count_batch_with_sam3(images, confidence_threshold, prompt)

        # 3. Fallback to YOLO
        if YOLO_AVAILABLE:
            if self.yolo_model is None:
                self._init_fallback_models()
            if self.yolo_model is not None:
                return self._count_batch_with_yolo(images, confidence_threshold)

        # Error case
        return [{
            "count": 0,
            "detections": [],
            "source": "error",
            "error": "No model available",
        } for _ in images]

    def _count_batch_with_sam3(
        self, images: List[Image.Image], confidence_threshold: float, prompt: str
    ) -> List[Dict[str, Any]]:
        """Count vehicles in a batch using SAM3."""
        import torch

        try:
            # Prepare batch inputs
            rgb_images = [img.convert("RGB") if img.mode != "RGB" else img for img in images]
            prompts = [prompt] * len(images)
            
            logger.info(f"[SAM3] Processing batch of {len(images)} images (prompt='{prompt}')")

            inputs = self.sam3_processor(
                images=rgb_images, text=prompts, return_tensors="pt", padding=True
            ).to(self.device)

            with torch.no_grad():
                outputs = self.sam3_model(**inputs)

            results_list = self.sam3_processor.post_process_instance_segmentation(
                outputs,
                threshold=confidence_threshold,
                mask_threshold=0.5,
                target_sizes=inputs.get("original_sizes").tolist(),
            )

            batch_results = []
            
            for idx, results in enumerate(results_list):
                masks = results.get("masks", [])
                boxes = results.get("boxes", [])
                scores = results.get("scores", [])

                n_raw_detections = len(masks) if hasattr(masks, "__len__") else 0
                
                detections = []
                valid_detections = []
                boxes_for_overlay = []
                skipped_cutoff = 0
                
                image = rgb_images[idx]
                img_width, img_height = image.size

                if n_raw_detections > 0:
                    for i in range(n_raw_detections):
                        score = float(scores[i].cpu()) if hasattr(scores[i], "cpu") else float(scores[i])
                        box = boxes[i].cpu().numpy() if hasattr(boxes[i], "cpu") else boxes[i]

                        box_dict = {
                            "xmin": float(box[0]),
                            "ymin": float(box[1]),
                            "xmax": float(box[2]),
                            "ymax": float(box[3]),
                        }

                        is_complete = self._is_fully_visible(box_dict, img_width, img_height)

                        detection = {
                            "class": prompt,
                            "confidence": score,
                            "box": box_dict,
                            "is_complete": is_complete,
                        }

                        detections.append(detection)
                        boxes_for_overlay.append((box, score, prompt, is_complete))

                        if is_complete:
                            valid_detections.append(detection)
                        else:
                            skipped_cutoff += 1

                overlay_b64 = self._create_sam3_overlay(image, masks, boxes_for_overlay)
                
                batch_results.append({
                    "count": len(valid_detections),
                    "detections": detections,
                    "overlay_image": overlay_b64,
                    "source": "sam3",
                })

            return batch_results

        except Exception as e:
            logger.error(f"[SAM3] Batch Error: {e}")
            # Fallback to YOLO if SAM3 fails
            if YOLO_AVAILABLE:
                 return self._count_batch_with_yolo(images, confidence_threshold)
            return [{"count": 0, "detections": [], "source": "error", "error": str(e)} for _ in images]

    def _count_batch_with_yolo(
        self, images: List[Image.Image], confidence_threshold: float
    ) -> List[Dict[str, Any]]:
        """Count vehicles in a batch using YOLO."""
        import numpy as np
        
        try:
            # Convert all to list of numpy arrays
            img_list = [np.array(img) for img in images]
            
            logger.info(f"[YOLO] Running batch detection on {len(images)} images...")
            results_list = self.yolo_model(img_list, conf=confidence_threshold, verbose=False)
            
            batch_outputs = []
            
            for idx, result in enumerate(results_list):
                detections = []
                boxes_overlay = []
                
                img_height, img_width = img_list[idx].shape[:2]
                valid_detections = []
                skipped_cutoff = 0

                if result.boxes is not None:
                    for box in result.boxes:
                        cls_id = int(box.cls.cpu().numpy()[0])
                        
                        if cls_id in self.vehicle_classes:
                            conf = float(box.conf.cpu().numpy()[0])
                            xyxy = box.xyxy.cpu().numpy()[0]
                            
                            box_dict = {
                                "xmin": float(xyxy[0]),
                                "ymin": float(xyxy[1]),
                                "xmax": float(xyxy[2]),
                                "ymax": float(xyxy[3]),
                            }
                            
                            is_complete = self._is_fully_visible(box_dict, img_width, img_height)
                            
                            detection = {
                                "class": self.vehicle_classes[cls_id],
                                "confidence": conf,
                                "box": box_dict,
                                "is_complete": is_complete,
                            }
                            
                            detections.append(detection)
                            boxes_overlay.append((xyxy, conf, self.vehicle_classes[cls_id], is_complete))
                            
                            if is_complete:
                                valid_detections.append(detection)
                            else:
                                skipped_cutoff += 1
                
                overlay_b64 = self._create_yolo_overlay(images[idx], boxes_overlay)
                
                batch_outputs.append({
                    "count": len(valid_detections),
                    "detections": detections,
                    "overlay_image": overlay_b64,
                    "source": "yolo"
                })
                
            return batch_outputs

        except Exception as e:
            logger.error(f"[YOLO] Batch Error: {e}")
            return [{"count": 0, "detections": [], "source": "error", "error": str(e)} for _ in images]


    def _create_sam3_overlay(
        self, image: Image.Image, masks, boxes: List
    ) -> Optional[str]:
        """Create overlay with SAM3 masks and bounding boxes."""
        try:
            return self._extracted_from__create_sam3_overlay_6(image, masks, boxes)
        except Exception as e:
            logger.error(f"[SAM3] Overlay error: {e}")
            import traceback

            traceback.print_exc()
            return None

    # TODO Rename this here and in `_create_sam3_overlay`
    def _extracted_from__create_sam3_overlay_6(self, image, masks, boxes):
        import matplotlib

        # Convert to RGBA for overlay
        overlay = image.convert("RGBA")

        # Overlay masks with rainbow colors
        if hasattr(masks, "__len__") and len(masks) > 0:
            masks_np = (
                masks.cpu().numpy() if hasattr(masks, "cpu") else np.array(masks)
            )
            n_masks = masks_np.shape[0] if len(masks_np.shape) > 2 else 1

            cmap = matplotlib.colormaps.get_cmap("rainbow").resampled(
                max(n_masks, 1)
            )

            for i in range(n_masks):
                mask = masks_np[i] if n_masks > 1 else masks_np
                mask_uint8 = (mask * 255).astype(np.uint8)

                # Get color from colormap
                color = tuple(
                    int(c * 255) for c in cmap(i / max(n_masks - 1, 1))[:3]
                )

                # Squeeze to ensure 2D (H, W)
                if mask_uint8.ndim > 2:
                    mask_uint8 = mask_uint8.squeeze()

                # Create colored overlay
                mask_img = Image.fromarray(mask_uint8, mode="L")
                color_overlay = Image.new("RGBA", image.size, color + (0,))
                alpha = mask_img.point(lambda v: int(v * 0.5))
                color_overlay.putalpha(alpha)
                overlay = Image.alpha_composite(overlay, color_overlay)

        # Convert back to RGB and draw boxes
        overlay_rgb = overlay.convert("RGB")
        draw = ImageDraw.Draw(overlay_rgb)

        for box_data in boxes:
            # Handle both old 3-tuple and new 4-tuple format
            if len(box_data) == 4:
                xyxy, conf, cls, is_complete = box_data
            else:
                xyxy, conf, cls = box_data
                is_complete = True

            x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])

            # Green for complete vehicles, orange dashed for cut-off
            if is_complete:
                color = "#22c55e"  # Green
                label = f"{cls} {conf:.0%}"
            else:
                color = "#f97316"  # Orange
                label = f"{cls} {conf:.0%} (cut)"

            # Draw box
            draw.rectangle(
                [x1, y1, x2, y2], outline=color, width=3 if is_complete else 2
            )

            # Draw label
            try:
                text_bbox = draw.textbbox((x1, y1 - 18), label)
                draw.rectangle(
                    [
                        text_bbox[0] - 2,
                        text_bbox[1] - 2,
                        text_bbox[2] + 2,
                        text_bbox[3] + 2,
                    ],
                    fill=color,
                )
                draw.text((x1, y1 - 18), label, fill="white")
            except:
                draw.text((x1, y1 - 18), label, fill=color)

        # Convert to base64
        buf = io.BytesIO()
        overlay_rgb.save(buf, format="JPEG", quality=85)
        return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"

    def _create_yolo_overlay(self, image: Image.Image, boxes: List) -> Optional[str]:
        """Create overlay with YOLO detection boxes."""
        try:
            overlay = image.copy().convert("RGB")
            draw = ImageDraw.Draw(overlay)

            for box_data in boxes:
                # Handle both old 3-tuple and new 4-tuple format
                if len(box_data) == 4:
                    xyxy, conf, cls, is_complete = box_data
                else:
                    xyxy, conf, cls = box_data
                    is_complete = True

                x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])

                # Green for complete vehicles, orange for cut-off
                if is_complete:
                    color = "#22c55e"  # Green
                    label = f"{cls} {conf:.0%}"
                else:
                    color = "#f97316"  # Orange
                    label = f"{cls} {conf:.0%} (cut)"

                # Draw box
                draw.rectangle(
                    [x1, y1, x2, y2], outline=color, width=3 if is_complete else 2
                )

                # Draw label
                try:
                    text_bbox = draw.textbbox((x1, y1 - 18), label)
                    draw.rectangle(
                        [
                            text_bbox[0] - 2,
                            text_bbox[1] - 2,
                            text_bbox[2] + 2,
                            text_bbox[3] + 2,
                        ],
                        fill=color,
                    )
                    draw.text((x1, y1 - 18), label, fill="white")
                except:
                    draw.text((x1, y1 - 18), label, fill=color)

            buf = io.BytesIO()
            overlay.save(buf, format="JPEG", quality=85)
            return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"

        except Exception as e:
            logger.error(f"[YOLO] Overlay error: {e}")
            return None


# Singleton instance
vehicle_counter = VehicleCounter()

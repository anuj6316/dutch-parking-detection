import os
import logging
from ultralytics import YOLO
from PIL import Image
from typing import List, Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

MODEL_PATH = os.getenv("MODEL_PATH")
if not MODEL_PATH:
    MODEL_PATH = "/app/yolo26s-obb-heavy-aug6/weights/best.pt"
    logger.info(f"Using default Model Path: {MODEL_PATH}")
else:
    logger.info(f"Model Path loaded from environment: {MODEL_PATH}")

class YOLODetector:
    def __init__(
        self,
        model_path: str = MODEL_PATH,
    ):
        self.model = YOLO(model_path)
        logger.info(f"[YOLO] Loaded model from {model_path}")

    def detect_parking_spaces(
        self, image: Image.Image, confidence: float = 0.15
    ) -> List[Dict[str, Any]]:
        """Detect parking spaces using YOLO with explicit .predict() pattern."""
        results = self.model.predict(
            source=image,
            imgsz=1024,
            conf=confidence,
            verbose=False,
            save=False,
            device="cpu"
        )

        logger.info(f"[YOLO] Results type: {type(results)}, length: {len(results)}")

        detections = []
        for result in results:
            logger.info(
                f"[YOLO] Result type: {type(result)}, has obb: {hasattr(result, 'obb')}, has boxes: {hasattr(result, 'boxes')}"
            )

            obb = getattr(result, "obb", None)
            boxes = getattr(result, "boxes", None)

            if obb is not None and len(obb) > 0:
                logger.info(f"[YOLO] Found {len(obb)} OBB detections")
                for obb_det in obb:
                    # Robustly handle dimensions for single detection
                    xyxy_np = obb_det.xyxy.cpu().numpy()
                    xyxy = xyxy_np[0].tolist() if xyxy_np.ndim > 1 else xyxy_np.tolist()
                    
                    # Extract OBB 8-point polygon coordinates
                    xyxyxyxy_np = obb_det.xyxyxyxy.cpu().numpy()
                    # Ensure it's flattened to a simple list of 8 floats
                    polygon = xyxyxyxy_np.flatten().tolist()
                    
                    conf_np = obb_det.conf.cpu().numpy()
                    conf = float(conf_np.item()) if conf_np.size == 1 else float(conf_np[0])
                    
                    cls_np = obb_det.cls.cpu().numpy()
                    cls = int(cls_np.item()) if cls_np.size == 1 else int(cls_np[0])

                    detections.append(
                        {
                            "bbox": [float(x) for x in xyxy],
                            "polygon": [float(x) for x in polygon],
                            "confidence": conf,
                            "class_id": cls,
                        }
                    )
            elif boxes is not None and len(boxes) > 0:
                logger.info(f"[YOLO] Found {len(boxes)} box detections")
                for box in boxes:
                    xyxy = box.xyxy[0].cpu().numpy()
                    
                    conf_np = box.conf.cpu().numpy()
                    conf = float(conf_np.item()) if conf_np.size == 1 else float(conf_np[0])
                    
                    cls_np = box.cls.cpu().numpy()
                    cls = int(cls_np.item()) if cls_np.size == 1 else int(cls_np[0])

                    detections.append(
                        {
                            "bbox": xyxy.tolist(),
                            "confidence": conf,
                            "class_id": cls,
                        }
                    )

        logger.info(f"[YOLO] Found {len(detections)} parking spaces")

        return detections

from ultralytics import YOLO
import cv2
import os
import numpy as np

# Load model
# model = YOLO("/home/mindmap/Desktop/dutch-parking-detection/runs/obb/trained_models/yolov26x/satellite_parking_final6/weights/best.pt")
model = YOLO("/home/mindmap/Desktop/dutch-parking-detection/yolov26x/yolov26x-dataset1234-310120265/weights/best.pt")

# Output crop directory
crop_dir = "/home/mindmap/Desktop/dutch-parking-detection/obb_crops_val"
os.makedirs(crop_dir, exist_ok=True)

# Run prediction
results = model.predict(
    source="/home/mindmap/Desktop/dutch-parking-detection/dataset/val/images",
    imgsz=1024,
    conf=0.25,
    save=True,
    name="home_runs",
    device="cuda"
)

crop_id = 0

for r in results:
    img = r.orig_img.copy()

    # OBB detections
    if r.obb is None:
        continue

    obb = r.obb.xyxyxyxy.cpu().numpy()  # shape: (N, 8)

    for box in obb:
        pts = box.reshape(4, 2).astype(np.float32)

        # Compute width & height of rotated box
        w = int(max(
            np.linalg.norm(pts[0]-pts[1]),
            np.linalg.norm(pts[2]-pts[3])
        ))
        h = int(max(
            np.linalg.norm(pts[1]-pts[2]),
            np.linalg.norm(pts[3]-pts[0])
        ))

        # Destination points for warp
        dst = np.array([
            [0,0],
            [w,0],
            [w,h],
            [0,h]
        ], dtype=np.float32)

        # Perspective transform
        M = cv2.getPerspectiveTransform(pts, dst)
        crop = cv2.warpPerspective(img, M, (w, h))

        # Save crop
        save_path = os.path.join(crop_dir, f"crop_{crop_id}.jpg")
        cv2.imwrite(save_path, crop)
        crop_id += 1

print(f"Saved {crop_id} OBB crops to {crop_dir}")

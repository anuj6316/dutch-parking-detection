import os
import glob
from ultralytics import YOLO
import torch
import gc
import cv2

# 1. Initialize YOLO-World Model
# Using 'l' (large) for better zero-shot performance. 'v2' is generally improved.
model_name = "yolov8l-worldv2.pt" 
print(f"Loading {model_name}...")
model = YOLO(model_name)

# 2. Define Custom Classes (Open Vocabulary)
classes = [
    "wheelchair parking symbol",
    "electric vehicle charging symbol", 
    "blue parking line",
    "text 'gereserveerd'",
    "yellow dashed line"
]
print(f"Setting classes: {classes}")
model.set_classes(classes)

# 3. Setup Paths
input_folder = "obb_crops_val"
output_folder = "experiments/yolo_world_results"
os.makedirs(output_folder, exist_ok=True)

# Get test images
image_paths = sorted(glob.glob(os.path.join(input_folder, "*.jpg")))[:20] # Test on 20 samples
# Add our specific test case
if os.path.exists("obb_crops/crop_28.jpg"):
    image_paths.append("obb_crops/crop_28.jpg")

print(f"Testing on {len(image_paths)} images...")

# 4. Run Inference
for img_path in image_paths:
    try:
        # Run prediction
        # conf=0.05 is quite low to catch faint symbols, typical for zero-shot
        results = model.predict(img_path, conf=0.05, save=False, verbose=False)
        
        # Save annotated image
        # plot() returns a numpy array (BGR)
        annotated_frame = results[0].plot()
        
        # Save using cv2
        save_path = os.path.join(output_folder, os.path.basename(img_path))
        cv2.imwrite(save_path, annotated_frame)
        
        # Print if detections found
        if len(results[0].boxes) > 0:
            print(f"Detected {len(results[0].boxes)} objects in {os.path.basename(img_path)}")
            for box in results[0].boxes:
                cls_id = int(box.cls)
                cls_name = classes[cls_id] if cls_id < len(classes) else str(cls_id)
                print(f" - {cls_name} ({box.conf.item():.2f})")
        
        # Memory cleanup
        del results, annotated_frame
        torch.cuda.empty_cache()
        gc.collect()

    except Exception as e:
        print(f"Error processing {img_path}: {e}")

print(f"\nDone! Results saved to {output_folder}")

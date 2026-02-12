import os
import glob
import torch
import gc
from PIL import Image, ImageDraw, ImageFont
from transformers import OwlViTProcessor, OwlViTForObjectDetection

# Model setup
model_id = "google/owlvit-base-patch32"
device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Loading model {model_id} on {device}...")
processor = OwlViTProcessor.from_pretrained(model_id)
model = OwlViTForObjectDetection.from_pretrained(model_id).to(device)

# Define prompts for Dutch parking markings
text_queries = [
    "wheelchair icon on road",
    "electric charging station",
    "text 'gereserveerd' on pavement",
    "blue parking line",
    "yellow line",
    "parked car",
    "empty parking space"
]

# Path setup
image_folder = "obb_crops_val"
output_folder = "experiments/owl_vit_results"
os.makedirs(output_folder, exist_ok=True)

image_paths = sorted(glob.glob(os.path.join(image_folder, "*.jpg")))
sample_size = 20
test_paths = image_paths[:sample_size]

print(f"Starting analysis on {len(test_paths)} images. Results will be saved to {output_folder}")

for image_path in test_paths:
    try:
        image = Image.open(image_path).convert("RGB")
        
        # Inference
        inputs = processor(text=[text_queries], images=image, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model(**inputs)

        logits = outputs.logits[0]
        boxes = outputs.pred_boxes[0]
        
        # Get scores and labels
        probs = torch.max(logits, dim=-1)
        scores = torch.sigmoid(probs.values)
        labels = probs.indices
        
        # DEBUG: Print max score for this image
        if scores.numel() > 0:
            print(f"Image {os.path.basename(image_path)}: Max score = {round(scores.max().item(), 4)}")

        # Lower threshold significantly for testing
        threshold = 0.05
        mask = scores > threshold
        
        scores = scores[mask]
        labels = labels[mask]
        boxes = boxes[mask]
        
        # Rescale boxes
        img_h, img_w = image.size[::-1]
        
        def box_cxcywh_to_xyxy(x):
            x_c, y_c, w, h = x.unbind(-1)
            b = [(x_c - 0.5 * w), (y_c - 0.5 * h),
                 (x_c + 0.5 * w), (y_c + 0.5 * h)]
            return torch.stack(b, dim=-1)

        boxes = box_cxcywh_to_xyxy(boxes)
        scale_fct = torch.stack([torch.tensor(img_w), torch.tensor(img_h), torch.tensor(img_w), torch.tensor(img_h)]).to(device)
        boxes = boxes * scale_fct
        
        # Visualization
        if len(labels) > 0:
            draw = ImageDraw.Draw(image)
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
            except:
                font = ImageFont.load_default()

            detected = False
            for box, score, label in zip(boxes, scores, labels):
                label_idx = label.item()
                if label_idx >= len(text_queries):
                    continue
                    
                box_list = [round(i, 2) for i in box.tolist()]
                label_text = text_queries[label_idx]
                
                # Filter out very small boxes or degenerate boxes if needed
                if (box_list[2] - box_list[0]) < 5 or (box_list[3] - box_list[1]) < 5:
                    continue

                draw.rectangle(box_list, outline="red", width=2)
                draw.text((box_list[0], box_list[1] - 15), f"{label_text} {round(score.item(), 2)}", fill="red", font=font)
                detected = True
            
            if detected:
                save_path = os.path.join(output_folder, os.path.basename(image_path))
                image.save(save_path)
        
        # Memory Management
        del inputs, outputs
        torch.cuda.empty_cache()
        gc.collect()

    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        torch.cuda.empty_cache()
        gc.collect()

print(f"\nAnalysis complete. Check the results in: {output_folder}")

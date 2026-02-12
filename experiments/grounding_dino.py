import os
import glob
import torch
import gc
from PIL import Image, ImageDraw, ImageFont
from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection

# Model setup
model_id = "rziga/mm_grounding_dino_large_all"
device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Loading model {model_id} on {device}...")
processor = AutoProcessor.from_pretrained(model_id)
model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id).to(device)

# Define prompts for Dutch parking markings
text_labels = [
    "wheelchair parking symbol . electric vehicle charging symbol . text 'gereserveerd' . blue line on road . yellow dashed line ."
]

# Path setup
image_folder = "obb_crops_val"
output_folder = "experiments/grounding_dino_results"
os.makedirs(output_folder, exist_ok=True)

image_paths = sorted(glob.glob(os.path.join(image_folder, "*.jpg")))
sample_size = 20
test_paths = image_paths[:sample_size]

print(f"Starting analysis on {len(test_paths)} images. Results will be saved to {output_folder}")

for image_path in test_paths:
    try:
        image = Image.open(image_path).convert("RGB")
        
        # Inference
        inputs = processor(images=image, text=text_labels, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model(**inputs)

        results = processor.post_process_grounded_object_detection(
            outputs,
            inputs.input_ids,
            threshold=0.3,
            text_threshold=0.25,
            target_sizes=[image.size[::-1]]
        )

        result = results[0]
        
        # Visualization
        if len(result["labels"]) > 0:
            draw = ImageDraw.Draw(image)
            # Try to load a font, fallback to default
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
            except:
                font = ImageFont.load_default()

            print(f"\n--- {os.path.basename(image_path)} ---")
            for box, score, label in zip(result["boxes"], result["scores"], result["labels"]):
                box = box.tolist()
                draw.rectangle(box, outline="red", width=3)
                draw.text((box[0], box[1] - 20), f"{label} {round(score.item(), 2)}", fill="red", font=font)
                print(f"Detected: [{label}] | Conf: {round(score.item(), 3)}")
            
            # Save the annotated image
            save_path = os.path.join(output_folder, os.path.basename(image_path))
            image.save(save_path)
        
        # Memory Management
        del inputs, outputs, results
        torch.cuda.empty_cache()
        gc.collect()

    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        torch.cuda.empty_cache()
        gc.collect()

print(f"\nAnalysis complete. Check the results in: {output_folder}")

import os
import torch
import gc
from PIL import Image
from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection

# Force CPU to avoid OOM
device = "cpu"

print(f"Loading model on {device}...")
model_id = "rziga/mm_grounding_dino_large_all"
processor = AutoProcessor.from_pretrained(model_id)
model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id).to(device)

text_labels = ["wheelchair parking symbol ."]
image_path = "obb_crops/crop_28.jpg"

print(f"Processing {image_path}...")
image = Image.open(image_path).convert("RGB")
inputs = processor(images=image, text=text_labels, return_tensors="pt").to(device)

with torch.no_grad():
    outputs = model(**inputs)

results = processor.post_process_grounded_object_detection(
    outputs,
    inputs.input_ids,
    threshold=0.1, # Lower threshold to be sure
    target_sizes=[image.size[::-1]]
)

result = results[0]
print(f"\n--- Analysis for {image_path} ---")
if len(result["labels"]) == 0:
    print("No icons detected. Trying 'white wheelchair symbol on ground'...")
    # Retry with different prompt
    text_labels = ["white wheelchair symbol on ground ."]
    inputs = processor(images=image, text=text_labels, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    result = processor.post_process_grounded_object_detection(
        outputs, inputs.input_ids, threshold=0.1, target_sizes=[image.size[::-1]]
    )[0]

for box, score, label in zip(result["boxes"], result["scores"], result["labels"]):
    box = [round(x, 2) for x in box.tolist()]
    print(f"Detected: [{label}] | Conf: {round(score.item(), 3)} | Box: {box}")

# Cleanup
del model, processor, inputs, outputs
gc.collect()

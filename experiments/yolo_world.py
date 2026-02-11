# from ultralytics import YOLO

# # Initialize a YOLO-World model
# model = YOLO("yolov8s-world.pt")  # or select yolov8m/l-world.pt

# # Define custom classes
# model.set_classes(["handicapped parking symbol", "private property sign"])

# # Save the model with the defined offline vocabulary
# model.save("custom_yolov8s.pt")

from ultralytics import YOLO

# Load your custom model
model = YOLO("custom_yolov8s.pt")

# Run inference to detect your custom classes
results = model.predict("/home/mindmap/Desktop/dutch-parking-detection/obb_crops_val/crop_28.jpg", save=True)

# Show results
results[0].show()
from ultralytics import YOLO

# model = YOLO("/home/mindmap/Desktop/dutch-parking-detection/utrecht_center_model/transfer-learning-obb-heavy-aug2/weights/best.pt") 
## able to find the road side parking but not as good as the heavy-aug6

# model = YOLO("/home/mindmap/Desktop/dutch-parking-detection/yolo26s-obb-heavy-aug6/weights/best.pt")
## This model is giving good result in general

# model = YOLO("/home/mindmap/Desktop/dutch-parking-detection/yolo26l-obb/yolo26l-obb-heavy-aug5/weights/best.pt")
## training in the progress 

# model = YOLO("/home/mindmap/Desktop/dutch-parking-detection/models/best_6.pt")

# model = YOLO("/home/mindmap/Desktop/dutch-parking-detection/yolov26x/yolov26x-dataset1234-310120265/weights/best.pt")
model = YOLO("/home/mindmap/Desktop/dutch-parking-detection/runs/obb/trained_models/yolov26x/satellite_parking_final6/weights/best.pt") ## LIVE
result = model.predict(
    # source="/home/mindmap/Desktop/dutch-parking-detection/backend/public/merged-images/amersfoort",
    source="/home/mindmap/Desktop/dutch-parking-detection/dataset/val/images",
    imgsz=1024,
    conf=0.25,
    save=True,
    name="home_runs",
    device="cpu"
)

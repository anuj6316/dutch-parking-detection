from ultralytics import YOLO

model = YOLO("/home/mindmap/Desktop/dutch-parking-detection/runs/obb/trained_models/yolov26x/yolov26x-dataset1234-02022026_2/weights/last.pt")

if __name__ == "__main__":
    results = model.train(
        resume=True
    )
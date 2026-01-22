from ultralytics import YOLO

model = YOLO("/home/anuj/Documents/dutch-parking-detection/yolo26s-obb-heavy-aug6/weights/best.pt")

result = model.predict(
    source="/home/anuj/Documents/dutch-parking-detection/new_frontend/public/merged-images/utrecht",
    imgsz=1024,
    conf=0.25,
    save=True,
    name="home_runs"
)
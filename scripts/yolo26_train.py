if __name__ == "__main__":
    import comet_ml
    import os
    
    ## Comet config
    comet_ml.init(api_key="6qDsDPfaQ1gZ0h421LcHsCX3d")
    os.environ['COMET_PROJECT_NAME'] = "yolov26x"
    os.environ['COMET_WORKSPACE'] = "anuj-kumar-0907"
    os.environ['COMET_MODE'] = 'online'
    os.environ['COMET_LOG_ASSETS'] = 'true'
    os.environ['COMET_LOG_PER_CLASS_METRICS'] = 'true'
    
    # Create experiment to log weights manually if needed
    experiment = comet_ml.Experiment(
        api_key="6qDsDPfaQ1gZ0h421LcHsCX3d",
        project_name="yolov26x",
        workspace="anuj-kumar-0907"
    )
    
    from ultralytics import YOLO
    
    model = YOLO("yolo26x-obb.pt")
    
    results = model.train(
        data="/home/mindmap/Desktop/dutch-parking-detection/scripts/data.yaml",
        epochs=2000,
        imgsz=1024,
        batch=3,
        project="trained_models/yolov26x",
        name="yolov26x-dataset1234-02022026_",
        device=0,
        patience=150,
        save_period=50,
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        weight_decay=0.01,
        warmup_epochs=10,
        warmup_momentum=0.8,
        warmup_bias_lr=0.1,
        box=7.5,
        cls=0.3,
        dfl=1.5,
        translate=0.2,
        degrees=180.0,
        scale=0.8,
        shear=2.5,
        perspective=0.0005,
        flipud=0.5,
        fliplr=0.5,
        mosaic=1.0,
        close_mosaic=15,
        mixup=0.05,
        bgr=0.5,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.7,
        overlap_mask=True,
        mask_ratio=4,
    )
    
    # After training completes, upload the final weights to Comet ML
    try:
        # Path to the best weights
        best_weights_path = f"yolov26x/yolov26x-dataset1234-31012026/weights/best.pt"
        last_weights_path = f"yolov26x/yolov26x-dataset1234-31012026/weights/last.pt"
        
        # Log the best model weights
        if os.path.exists(best_weights_path):
            experiment.log_model("best_model", best_weights_path)
            print(f"✓ Uploaded best weights to Comet ML: {best_weights_path}")
        
        # Log the last model weights
        if os.path.exists(last_weights_path):
            experiment.log_model("last_model", last_weights_path)
            print(f"✓ Uploaded last weights to Comet ML: {last_weights_path}")
        
        # Log all saved checkpoints (from save_period=50)
        weights_dir = f"yolov26x/yolov26x-dataset1234-31012026/weights"
        if os.path.exists(weights_dir):
            for weight_file in os.listdir(weights_dir):
                if weight_file.startswith("epoch") and weight_file.endswith(".pt"):
                    weight_path = os.path.join(weights_dir, weight_file)
                    model_name = weight_file.replace(".pt", "")
                    experiment.log_model(model_name, weight_path)
                    print(f"✓ Uploaded checkpoint to Comet ML: {weight_file}")
        
    except Exception as e:
        print(f"Error uploading weights to Comet ML: {e}")
    
    finally:
        # End the experiment
        experiment.end()
        print("Training complete and weights uploaded to Comet ML!")
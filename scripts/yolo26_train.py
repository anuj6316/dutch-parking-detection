
import os
import time
import comet_ml
from ultralytics import YOLO

if __name__ == "__main__":

    # ==============================
    # COMET SETUP
    # ==============================
    # In terminal:
    # export COMET_API_KEY="your_key"
    comet_api_key = "6qDsDPfaQ1gZ0h421LcHsCX3d"

    experiment = comet_ml.Experiment(
        api_key=comet_api_key,
        project_name="yolov26x",
        workspace="anuj-kumar-0907",
        auto_metric_logging=True,
    )

    experiment.add_tag("satellite-parking")
    experiment.add_tag("aerial-detection")

    # ==============================
    # LOAD MODEL
    # ==============================
    model = YOLO("yolo26x-obb.pt")

    # ==============================
    # REAL-TIME BEST.PT UPLOAD
    # ==============================
    last_uploaded = {"best": None}

    def upload_best_to_comet(trainer):
        try:
            best_path = str(getattr(trainer, "best", ""))

            if not best_path or not os.path.exists(best_path):
                return

            for _ in range(5):
                if os.path.getsize(best_path) > 0:
                    break
                time.sleep(0.2)

            if last_uploaded["best"] != best_path:
                experiment.log_model(
                    name="best_model",
                    file_or_folder=best_path,
                    overwrite=True,
                )
                last_uploaded["best"] = best_path
                print("✅ Uploaded new best.pt to Comet")

        except Exception as e:
            print(f"Comet upload error: {e}")

    model.add_callback("on_model_save", upload_best_to_comet)

    # ==============================
    # TRAINING
    # ==============================
    results = model.train(
        data="/home/mindmap/Desktop/dutch-parking-detection/scripts/data.yaml",
        epochs=3000,
        imgsz=1024,
        batch=2,
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
        degrees=90.0,
        scale=0.8,
        shear=2.5,
        perspective=0.0005,
        flipud=0.5,
        fliplr=0.5,
        mosaic=0.4,
        close_mosaic=15,
        mixup=0.05,
        bgr=0.5,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.7,
        overlap_mask=True,
        mask_ratio=4,
    )
    # results = model.train(

    #     # -------- DATA --------
    #     data="/home/mindmap/Desktop/dutch-parking-detection/scripts/data.yaml",

    #     # -------- CORE --------
    #     epochs=3000,              # good for ~2000 images
    #     imgsz=1024,               # safer for VRAM (1536 if possible)
    #     batch=2,
    #     # accumulate=4,             # simulate batch 12
    #     device=0,

    #     # -------- OPTIMIZER --------
    #     optimizer="AdamW",
    #     lr0=0.0002,               # reduced for small batch
    #     lrf=0.05,
    #     momentum=0.9,
    #     weight_decay=0.0005,

    #     # -------- WARMUP --------
    #     warmup_epochs=10,
    #     warmup_momentum=0.85,
    #     warmup_bias_lr=0.05,

    #     # -------- LOSS --------
    #     box=12.0,
    #     cls=0.2,
    #     dfl=2.5,

    #     # -------- AUGMENTATION --------
    #     degrees=7.0,
    #     translate=0.08,
    #     scale=0.25,
    #     shear=0.3,
    #     perspective=0.0001,

    #     fliplr=0.5,
    #     flipud=0.0,

    #     mosaic=0.4,
    #     close_mosaic=20,
    #     mixup=0.0,
    #     copy_paste=0.0,

    #     hsv_h=0.01,
    #     hsv_s=0.4,
    #     hsv_v=0.3,

    #     # -------- OBB --------
    #     overlap_mask=True,
    #     mask_ratio=4,

    #     # -------- CONTROL --------
    #     multi_scale=True,
    #     patience=200,
    #     # save_period=25,

    #     # -------- OUTPUT --------
    #     project="trained_models/yolov26x",
    #     name="satellite_parking_final",
    # )

    # ==============================
    # FINAL SAFETY UPLOAD
    # ==============================
    try:
        run_dir = "trained_models/yolov26x/satellite_parking_final/weights"

        for f in ["best.pt", "last.pt"]:
            p = os.path.join(run_dir, f)
            if os.path.exists(p):
                experiment.log_model(f.replace(".pt", ""), p)

    except Exception as e:
        print(e)

    finally:
        experiment.end()

    print("🎯 Training complete!")


# if __name__ == "__main__":
#     import comet_ml
#     import os
    
#     ## Comet config
#     comet_ml.init(api_key="6qDsDPfaQ1gZ0h421LcHsCX3d")
#     os.environ['COMET_PROJECT_NAME'] = "yolov26x"
#     os.environ['COMET_WORKSPACE'] = "anuj-kumar-0907"
#     os.environ['COMET_MODE'] = 'online'
#     os.environ['COMET_LOG_ASSETS'] = 'true'
#     os.environ['COMET_LOG_PER_CLASS_METRICS'] = 'true'
    
#     # Create experiment to log weights manually if needed
#     experiment = comet_ml.Experiment(
#         project_name="yolov26x",
#         workspace="anuj-kumar-0907"
#     )
    
#     from ultralytics import YOLO
    
#     model = YOLO("yolo26x-obb.pt")
    
    
#     # After training completes, upload the final weights to Comet ML
#     try:
#         # Path to the best weights
#         best_weights_path = f"yolov26x/yolov26x-dataset1234-31012026/weights/best.pt"
#         last_weights_path = f"yolov26x/yolov26x-dataset1234-31012026/weights/last.pt"
        
#         # Log the best model weights
#         if os.path.exists(best_weights_path):
#             experiment.log_model("best_model", best_weights_path)
#             print(f"✓ Uploaded best weights to Comet ML: {best_weights_path}")
        
#         # Log the last model weights
#         if os.path.exists(last_weights_path):
#             experiment.log_model("last_model", last_weights_path)
#             print(f"✓ Uploaded last weights to Comet ML: {last_weights_path}")
        
#         # Log all saved checkpoints (from save_period=50)
#         weights_dir = f"yolov26x/yolov26x-dataset1234-31012026/weights"
#         if os.path.exists(weights_dir):
#             for weight_file in os.listdir(weights_dir):
#                 if weight_file.startswith("epoch") and weight_file.endswith(".pt"):
#                     weight_path = os.path.join(weights_dir, weight_file)
#                     model_name = weight_file.replace(".pt", "")
#                     experiment.log_model(model_name, weight_path)
#                     print(f"✓ Uploaded checkpoint to Comet ML: {weight_file}")
        
#     except Exception as e:
#         print(f"Error uploading weights to Comet ML: {e}")
    
#     finally:
#         # End the experiment
#         experiment.end()
#         print("Training complete and weights uploaded to Comet ML!")

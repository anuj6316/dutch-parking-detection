# Project Improvements TODO

## Backend (Parking Detection Pipeline)
- [ ] **Parallelize Tile Processing:** Currently, tiles are processed sequentially in `PipelineOrchestrator.run`. Implement `asyncio.gather` or a process pool to run YOLO detection on multiple tiles simultaneously.
- [ ] **Externalize Hyperparameters:** Move merge thresholds (e.g., `max_distance=50.0`, `iou_threshold=0.1`) from `obb_merger.py` into `config.py` (via Pydantic settings).
- [ ] **Batch YOLO Inference:** Optimize performance by passing a list of images to `self.model.predict()` rather than calling it per-tile.
- [ ] **Memory Management:** Monitor memory pressure when decoding many high-resolution Base64 strings. Consider implementing a generator pattern or temporary disk caching for massive area requests.

## Frontend (Analysis Hook)
- [ ] **Granular Error Reporting:** In `useParkingAnalysis.ts`, provide specific UI feedback if only a subset of tiles fail, rather than a generic error.
- [ ] **Configurable Grid Size:** Allow the user to define the grid dimensions (currently fixed or derived from constants) through the UI for more flexible custom area selection.

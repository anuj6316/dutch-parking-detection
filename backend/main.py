from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
from pydantic import BaseModel
import logging
import asyncio
import os
import base64
import json

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import settings
from pipeline import PipelineOrchestrator

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI()

origins = []
for o in settings.ALLOWED_ORIGINS:
    o = o.strip().rstrip("/")
    if o:
        origins.append(o)
        # Also allow the origin with a trailing slash just in case
        origins.append(o + "/")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = PipelineOrchestrator()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[job_id] = websocket
        logger.info(f"[WS] Connected job_id: {job_id}")

    def disconnect(self, job_id: str):
        if job_id in self.active_connections:
            del self.active_connections[job_id]
            logger.info(f"[WS] Disconnected job_id: {job_id}")

    async def send_log(self, job_id: str, message: Dict):
        if job_id in self.active_connections:
            try:
                await self.active_connections[job_id].send_json(message)
            except Exception as e:
                logger.error(f"[WS] Error sending log to {job_id}: {e}")
                self.disconnect(job_id)

manager = ConnectionManager()
active_tasks: Dict[str, asyncio.Task] = {}


class TilePayload(BaseModel):
    image_base64: str
    tile_index: int
    bounds: Dict[str, float]


class TileAnalysisRequest(BaseModel):
    tiles: List[TilePayload]
    confidence_threshold: float = 0.25
    count_vehicles: bool = True
    job_id: str = "default"  # Optional for legacy calls


@app.post("/cancel-analysis/{job_id}")
async def cancel_analysis(job_id: str):
    """Terminate a running analysis task."""
    if job_id in active_tasks:
        task = active_tasks[job_id]
        task.cancel()
        logger.info(f"[API] Cancelled task for job_id: {job_id}")
        return {"status": "cancelled", "job_id": job_id}
    else:
        logger.warning(f"[API] No active task found for job_id: {job_id}")
        return {"status": "not_found", "job_id": job_id}


@app.websocket("/ws/logs/{job_id}")
async def websocket_logs(websocket: WebSocket, job_id: str):
    await manager.connect(job_id, websocket)
    try:
        while True:
            # Keep connection open
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(job_id)
    except Exception as e:
        logger.error(f"[WS] Error in logs socket: {e}")
        manager.disconnect(job_id)


@app.post("/analyze-tiles/")
async def analyze_tiles(request: TileAnalysisRequest):
    """
    Standard HTTP endpoint for analysis. 
    If 'job_id' is provided, streams logs to the connected WebSocket.
    """
    job_id = request.job_id
    logger.info(f"[API] Received {len(request.tiles)} tiles (Job: {job_id})")
    
    tiles_data = [
        {"image_base64": t.image_base64, "tile_index": t.tile_index, "bounds": t.bounds}
        for t in request.tiles
    ]
    
    async def run_pipeline():
        # Define a callback to push logs to WebSocket
        async def log_callback(update):
            if job_id:
                await manager.send_log(job_id, update)

        final_result = {}
        try:
            # Run pipeline with log callback
            async for update in pipeline.run(tiles_data, request.confidence_threshold):
                await log_callback(update)
                if update["type"] == "final_result":
                    final_result = update["data"]
            return final_result
        except asyncio.CancelledError:
            logger.info(f"[Task] Job {job_id} was cancelled internally")
            await manager.send_log(job_id, {"type": "log", "message": "⚠️ Analysis terminated by user."})
            await manager.send_log(job_id, {"type": "error", "message": "Job terminated."})
            raise
        finally:
            if job_id in active_tasks:
                del active_tasks[job_id]

    # Create and track the task
    task = asyncio.create_task(run_pipeline())
    active_tasks[job_id] = task
    
    try:
        return await task
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Client Closed Request / Job Cancelled")
    except Exception as e:
        logger.error(f"[API] Error in job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def read_root():
    return {"message": "Modular Parking Detection API"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "pipeline": "modular"}


SAVE_DIR = settings.SAVE_DIR


class SaveImagesRequest(BaseModel):
    images: List[Dict[str, Any]]
    municipality: str


@app.post("/save-images/")
async def save_images(request: SaveImagesRequest):
    """Save merged images to local directory."""
    logger.info(
        f"[API] Saving {len(request.images)} images for municipality: {request.municipality}"
    )

    municipality_dir = SAVE_DIR / request.municipality
    municipality_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    for img in request.images:
        index = img.get("index", 0)
        image_base64 = img.get("image_base64", "")
        hash_val = img.get("hash")
        
        if hash_val:
            file_name = f"{hash_val}.jpg"
        else:
            file_name = f"merged-{request.municipality}-{str(index).zfill(3)}.jpg"
            
        file_path = municipality_dir / file_name

        if file_path.exists():
            logger.info(f"[API] Skipping already saved image: {file_path}")
            saved_files.append(str(file_path))
            continue

        try:
            image_data = base64.b64decode(image_base64)
            with open(file_path, "wb") as f:
                f.write(image_data)
            saved_files.append(str(file_path))
            logger.info(f"[API] Saved: {file_path}")
        except Exception as e:
            logger.error(f"[API] Failed to save {file_path}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save image: {e}")

    return {"status": "success", "saved_count": len(saved_files), "files": saved_files}
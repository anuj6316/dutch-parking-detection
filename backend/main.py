from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
import logging
import asyncio
import os
import base64
import json
from pathlib import Path

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from dotenv import load_dotenv
load_dotenv()

from pipeline import PipelineOrchestrator

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI()

raw_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
origins = []
for o in raw_origins:
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


class TilePayload(BaseModel):
    image_base64: str
    tile_index: int
    bounds: Dict[str, float]


class TileAnalysisRequest(BaseModel):
    tiles: List[TilePayload]
    confidence_threshold: float = 0.25
    count_vehicles: bool = True


@app.post("/analyze-tiles/")
async def analyze_tiles(request: TileAnalysisRequest):
    """Legacy sequential endpoint (returns all at once)."""
    logger.info(f"[API] Received {len(request.tiles)} tiles (Sequential)")
    
    tiles_data = [
        {"image_base64": t.image_base64, "tile_index": t.tile_index, "bounds": t.bounds}
        for t in request.tiles
    ]
    
    final_result = {}
    async for update in pipeline.run(tiles_data, request.confidence_threshold):
        if update["type"] == "final_result":
            final_result = update["data"]
    
    return final_result


@app.post("/analyze-tiles-stream/")
async def analyze_tiles_stream(request: TileAnalysisRequest):
    """Streaming endpoint for real-time progress and logs."""
    logger.info(f"[API] Received {len(request.tiles)} tiles (Streaming)")

    tiles_data = [
        {"image_base64": t.image_base64, "tile_index": t.tile_index, "bounds": t.bounds}
        for t in request.tiles
    ]

    async def event_generator():
        # Yield an initial message to immediately open the connection and send headers
        yield json.dumps({"type": "log", "message": "Connection established. Starting analysis..."}) + "\n"
        
        try:
            async for update in pipeline.run(tiles_data, request.confidence_threshold):
                yield json.dumps(update) + "\n"
        except Exception as e:
            logger.error(f"Error in event_generator: {e}")
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson"
    )


@app.get("/")
def read_root():
    return {"message": "Modular Parking Detection API"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "pipeline": "modular"}


SAVE_DIR = Path(
    "./public/merged-images"
)


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
        file_name = f"merged-{request.municipality}-{str(index).zfill(3)}.jpg"
        file_path = municipality_dir / file_name

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
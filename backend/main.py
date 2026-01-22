from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
import logging
import asyncio
import os
import base64
from pathlib import Path

from fastapi.middleware.cors import CORSMiddleware

from pipeline import PipelineOrchestrator

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    """Run the complete modular detection pipeline."""
    logger.info(f"[API] Received {len(request.tiles)} tiles")

    tiles_data = [
        {"image_base64": t.image_base64, "tile_index": t.tile_index, "bounds": t.bounds}
        for t in request.tiles
    ]

    result = await pipeline.run(tiles_data, request.confidence_threshold)

    return result


@app.get("/")
def read_root():
    return {"message": "Modular Parking Detection API"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "pipeline": "modular"}


SAVE_DIR = Path(
    "/home/mindmap/Documents/dutch-parking-detection/new_frontend/public/merged-images"
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

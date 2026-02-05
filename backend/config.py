import os
from pathlib import Path
from dotenv import load_dotenv

# Load env vars from the root .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    # Model Configuration
    SKIP_SAM3_LOADING: bool = os.getenv("SKIP_SAM3_LOADING", "False").lower() == "true"
    MODEL_PATH: str = os.getenv("MODEL_PATH", str(Path(__file__).parent.parent / "yolo26s-obb-heavy-aug6/weights/best.pt"))
    
    # API Configuration
    ALLOWED_ORIGINS: list[str] = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    
    # Pipeline Configuration
    TILE_SIZE: int = int(os.getenv("TILE_SIZE", 256))
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", 0.25))
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    SAVE_DIR: Path = BASE_DIR / "backend" / "public" / "merged-images"

settings = Settings()

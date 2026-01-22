"""
VLM Verifier using Gemini 2.5 Flash for parking spot availability verification.

Uses the latest Google GenAI SDK (google-genai) for accurate, fast image analysis.
Updated to use the new SDK structure with genai.Client() and types.Part.
"""

import os
import io
import base64
import json
import re
from typing import Dict, Any
from PIL import Image
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Initialize Gemini with new SDK
GEMINI_AVAILABLE = False
client = None

try:
    from google import genai
    from google.genai import types
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        # New SDK uses Client with api_key parameter
        client = genai.Client(api_key=api_key)
        GEMINI_AVAILABLE = True
        print(f"[VLM] Gemini 2.5 Flash initialized with new SDK (api_key: {api_key[:15]}...)")
    else:
        print("[VLM] No GOOGLE_API_KEY found in environment")
except ImportError as e:
    print(f"[VLM] google-genai not installed. Run: pip install google-genai")
    print(f"[VLM] Import error: {e}")
except Exception as e:
    print(f"[VLM] Error initializing Gemini: {e}")


class VLMVerifier:
    """
    Uses Gemini 2.5 Flash to verify parking spot availability.
    
    Key improvements in this version:
    - Uses latest google-genai SDK
    - JSON response mode for structured output
    - Improved prompting with clearer instructions
    - Better error handling
    """
    
    def __init__(self):
        self.client = client
        self.available = GEMINI_AVAILABLE
        self.model = "gemini-2.5-pro"  # Latest model
        
        if self.available:
            print(f"[VLM] VLMVerifier ready with {self.model}")
        else:
            print("[VLM] VLMVerifier not available - check GOOGLE_API_KEY and install google-genai")
    
    def verify_parking_space(
        self, 
        image: Image.Image,
        vehicle_count: int = 0,
        vehicle_boxes: list = None,
        area_sq_meters: float = 0,
        estimated_capacity: int = 0,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze a cropped parking space image with SAM3 detection context.
        
        Args:
            image: PIL Image of the cropped parking space
            vehicle_count: Number of vehicles detected by SAM3
            vehicle_boxes: List of vehicle detection boxes from SAM3
            area_sq_meters: Total area of parking space in square meters
            estimated_capacity: Estimated number of spots based on area
            timeout: Request timeout in seconds (not used in new SDK)
            
        Returns:
            {
                "is_available": bool,
                "empty_spots": int,
                "vehicles_confirmed": int,
                "reason": str,
                "source": "gemini" | "error"
            }
        """
        # IMMEDIATE DISABLE for usage limits or user request
        # Returns NaNs/None as placeholders
        return {
            "is_available": None,
            "vehicles_confirmed": None,
            "empty_spots": None,
            "total_capacity": estimated_capacity,
            "reason": "VLM Disabled (NaN)",
            "source": "disabled"
        }


    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the VLM response to extract vehicle count and empty spots."""
        try:
           # Legacy parsing code or dummy
           return {}
        except:
           return {}


# Singleton instance
vlm_verifier = VLMVerifier()

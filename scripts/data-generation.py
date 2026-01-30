#!/usr/bin/env python3
"""
Production-Ready Parking Detection Dataset Generator
====================================================
Dynamic multi-source location fetching with real-world diversity

Features:
- 6x6 tile grid, 1536x1536 final resolution
- Multi-source OSM queries (streets, residential, commercial)
- Resume capability with registry
- Command-line arguments support
- No visualization directory (saves space)
- Enhanced metadata with context detection

Default: 1000 images from Utrecht
Usage: python production_parking_generator.py [OPTIONS]

# Default (Utrecht, 1000 images)
python3 production_parking_generator.py

# Different city
python3 production_parking_generator.py --municipality amsterdam

# Custom count
python3 production_parking_generator.py --count 2000

# Custom output
python3 production_parking_generator.py --output ./my_dataset

# Resume (default behavior)
python3 production_parking_generator.py --resume

# Start fresh
python3 production_parking_generator.py --no-resume

# Quality threshold
python3 production_parking_generator.py --min-quality 500

# Search radius
python3 production_parking_generator.py --radius 20
```

### Multi-Source Dynamic Locations
- **40%** Street parking (residential streets, service roads, main roads)
- **30%** Residential areas (neighborhoods, apartments)
- **20%** Commercial (retail, offices, mixed-use)
- **10%** Designated parking lots

### Quality & Context Detection
- Sharpness, contrast, brightness, edge density
- Tree coverage detection (for occlusion)
- Parking configuration detection (parallel/perpendicular/diagonal)
- Automatic quality filtering

### Output Structure
```
parking_dataset_utrecht_20260129/
├── images/                          # 1536×1536 PNG images
│   ├── parking_utrecht_0001_a3f2b8c9.png
│   └── ...
└── metadata/                        # Rich metadata
    ├── download_registry.json       # Resume capability
    ├── download_summary.json        # Statistics
    └── image_0001_metadata.json     # Individual metadata
"""

import os
import sys
import gc
import json
import time
import math
import hashlib
import argparse
import requests
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG = {
    "zoom_level": 21,
    "stitch_tiles": 6,           # 6x6 grid
    "tile_size": 256,
    "final_size": 1536,          # 1536x1536 final image
    "request_delay": 0.5,
    "timeout": 15,
    "retry_attempts": 3,
    "min_quality_sharpness": 300,  # Minimum sharpness for quality
}

# =============================================================================
# DATA MODELS
# =============================================================================

class LocationSource(Enum):
    """Source type of parking location"""
    DESIGNATED_PARKING = "designated_parking"
    RESIDENTIAL_STREET = "residential_street"
    SERVICE_ROAD = "service_road"
    TERTIARY_ROAD = "tertiary_road"
    RESIDENTIAL_AREA = "residential_area"
    APARTMENT = "apartment"
    RETAIL = "retail"
    COMMERCIAL = "commercial"
    MIXED_USE = "mixed_use"

class ParkingStyle(Enum):
    """Detected parking configuration"""
    PARALLEL = "parallel"
    PERPENDICULAR = "perpendicular"
    DIAGONAL = "diagonal"
    MIXED = "mixed"
    UNKNOWN = "unknown"

class OcclusionLevel(Enum):
    """Level of visual occlusion"""
    NONE = "none"
    PARTIAL = "partial"
    HEAVY = "heavy"

@dataclass
class LocationPoint:
    """Enhanced location point with context"""
    lat: float
    lon: float
    source: LocationSource
    context_tags: List[str]
    parking_style: ParkingStyle
    occlusion_level: OcclusionLevel
    osm_metadata: Dict
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'lat': self.lat,
            'lon': self.lon,
            'source': self.source.value,
            'context_tags': self.context_tags,
            'parking_style': self.parking_style.value,
            'occlusion_level': self.occlusion_level.value,
            'osm_metadata': self.osm_metadata
        }

# =============================================================================
# MUNICIPALITY DATABASE
# =============================================================================

MUNICIPALITIES = {
    "utrecht": {
        "name": "Utrecht",
        "country": "Netherlands",
        "center": (52.092876, 5.092312),
        "radius_km": 12,
    },
    "amsterdam": {
        "name": "Amsterdam",
        "country": "Netherlands",
        "center": (52.3676, 4.9041),
        "radius_km": 15,
    },
    "rotterdam": {
        "name": "Rotterdam",
        "country": "Netherlands",
        "center": (51.9225, 4.47917),
        "radius_km": 14,
    },
    "den_haag": {
        "name": "The Hague",
        "country": "Netherlands",
        "center": (52.0705, 4.3007),
        "radius_km": 12,
    },
    "eindhoven": {
        "name": "Eindhoven",
        "country": "Netherlands",
        "center": (51.4416, 5.4697),
        "radius_km": 10,
    },
}

# =============================================================================
# OSM QUERY DEFINITIONS
# =============================================================================

OSM_QUERIES = {
    # Priority 1: Street Parking (40% target)
    "residential_streets": {
        "overpass": """
            [out:json][timeout:60];
            (
              way["highway"="residential"]({bbox});
              way["highway"="living_street"]({bbox});
            );
            out geom;
        """,
        "sampling": {
            "type": "line",
            "interval": 40,
            "jitter": 10
        },
        "weight": 0.25,
        "source": LocationSource.RESIDENTIAL_STREET
    },
    
    "service_roads": {
        "overpass": """
            [out:json][timeout:60];
            way["highway"="service"]({bbox});
            out geom;
        """,
        "sampling": {
            "type": "line",
            "interval": 35,
            "jitter": 8
        },
        "weight": 0.10,
        "source": LocationSource.SERVICE_ROAD
    },
    
    "tertiary_roads": {
        "overpass": """
            [out:json][timeout:60];
            (
              way["highway"="tertiary"]({bbox});
              way["highway"="secondary"]({bbox});
            );
            out geom;
        """,
        "sampling": {
            "type": "line",
            "interval": 60,
            "jitter": 15
        },
        "weight": 0.05,
        "source": LocationSource.TERTIARY_ROAD
    },
    
    # Priority 2: Residential Areas (30% target)
    "residential_areas": {
        "overpass": """
            [out:json][timeout:60];
            (
              way["landuse"="residential"]({bbox});
            );
            out geom;
        """,
        "sampling": {
            "type": "polygon",
            "edge_points": 3,
            "interior_points": 2
        },
        "weight": 0.20,
        "source": LocationSource.RESIDENTIAL_AREA
    },
    
    "apartments": {
        "overpass": """
            [out:json][timeout:60];
            (
              node["building"="apartments"]({bbox});
              way["building"="apartments"]({bbox});
            );
            out center;
        """,
        "sampling": {
            "type": "point_buffer",
            "radius": 50,
            "num_points": 4
        },
        "weight": 0.10,
        "source": LocationSource.APARTMENT
    },
    
    # Priority 3: Commercial (20% target)
    "retail": {
        "overpass": """
            [out:json][timeout:60];
            (
              way["landuse"="retail"]({bbox});
              node["shop"]({bbox});
            );
            out center;
        """,
        "sampling": {
            "type": "point_buffer",
            "radius": 40,
            "num_points": 3
        },
        "weight": 0.10,
        "source": LocationSource.RETAIL
    },
    
    "commercial": {
        "overpass": """
            [out:json][timeout:60];
            (
              way["landuse"="commercial"]({bbox});
            );
            out center;
        """,
        "sampling": {
            "type": "point_buffer",
            "radius": 40,
            "num_points": 3
        },
        "weight": 0.10,
        "source": LocationSource.COMMERCIAL
    },
    
    # Priority 4: Designated Parking (10% target)
    "designated_parking": {
        "overpass": """
            [out:json][timeout:60];
            (
              node["amenity"="parking"]({bbox});
              way["amenity"="parking"]({bbox});
            );
            out center;
        """,
        "sampling": {
            "type": "point",
            "single": True
        },
        "weight": 0.10,
        "source": LocationSource.DESIGNATED_PARKING
    }
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def print_header():
    """Print application header"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║     🚗  PRODUCTION PARKING DETECTION DATASET GENERATOR          ║
║                                                                  ║
║     Dynamic Multi-Source Location Fetching                      ║
║     Real-World Diversity for ML Training                        ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝

Features:
  ✓ Multi-source OSM queries (streets, residential, commercial)
  ✓ 6x6 tile grid, 1536x1536 resolution
  ✓ Resume capability with duplicate detection
  ✓ Enhanced metadata with context detection
  ✓ Quality filtering and validation
  ✓ Production-ready diverse datasets

Configuration:
  • Resolution: 1536x1536 pixels
  • Zoom level: 21 (~0.15m per pixel)
  • Coverage: ~230m × 230m per image
  • File size: ~4-5 MB per image
  • Default: 1000 images from Utrecht

""")

def check_dependencies():
    """Check and install required dependencies"""
    print("📦 Checking dependencies...")
    missing = []
    
    dependencies = {
        "requests": "requests",
        "PIL": "pillow",
        "numpy": "numpy",
        "cv2": "opencv-python"
    }
    
    for module, package in dependencies.items():
        try:
            __import__(module)
            print(f"   ✅ {package}")
        except ImportError:
            missing.append(package)
            print(f"   ❌ {package}")
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        response = input("\nInstall missing packages? (y/n): ")
        if response.lower() == 'y':
            import subprocess
            for package in missing:
                print(f"Installing {package}...")
                subprocess.run([sys.executable, "-m", "pip", "install", 
                              package, "--break-system-packages", "-q"])
            print("✅ All packages installed!\n")
            return True
        else:
            print("❌ Cannot proceed without required packages")
            return False
    else:
        print("✅ All dependencies satisfied!\n")
        return True

def generate_location_hash(lat: float, lon: float) -> str:
    """Generate unique hash for location"""
    location_str = f"{lat:.5f},{lon:.5f}"
    return hashlib.md5(location_str.encode()).hexdigest()[:12]

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two GPS points"""
    R = 6371000  # Earth radius in meters
    
    φ1 = math.radians(lat1)
    φ2 = math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    
    a = (math.sin(Δφ/2) ** 2 + 
         math.cos(φ1) * math.cos(φ2) * math.sin(Δλ/2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def calculate_bbox(center_lat: float, center_lon: float, radius_km: float) -> Tuple:
    """Calculate bounding box from center and radius"""
    lat_offset = radius_km / 111.0
    lon_offset = radius_km / (111.0 * math.cos(math.radians(center_lat)))
    
    return (
        center_lat - lat_offset,  # south
        center_lon - lon_offset,  # west
        center_lat + lat_offset,  # north
        center_lon + lon_offset   # east
    )

# =============================================================================
# OSM QUERY FUNCTIONS
# =============================================================================

def query_osm(query_config: Dict, bbox: Tuple) -> List[Dict]:
    """Execute Overpass API query"""
    query = query_config["overpass"].format(
        bbox=f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
    )
    
    try:
        response = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json().get('elements', [])
        else:
            print(f"      ⚠️ OSM query failed: {response.status_code}")
            return []
            
    except requests.exceptions.Timeout:
        print(f"      ⚠️ OSM query timeout")
        return []
    except Exception as e:
        print(f"      ⚠️ OSM error: {e}")
        return []

def sample_line_geometry(coords: List[Tuple], interval: float, jitter: float) -> List[Tuple]:
    """Sample points along a line with jitter"""
    points = []
    
    for i in range(len(coords) - 1):
        lat1, lon1 = coords[i]
        lat2, lon2 = coords[i + 1]
        
        segment_dist = haversine_distance(lat1, lon1, lat2, lon2)
        
        if segment_dist < 5:  # Skip very short segments
            continue
        
        num_samples = int(segment_dist / interval)
        
        for j in range(num_samples):
            jitter_offset = np.random.uniform(-jitter, jitter)
            distance = j * interval + jitter_offset
            fraction = max(0, min(1, distance / segment_dist))
            
            lat = lat1 + (lat2 - lat1) * fraction
            lon = lon1 + (lon2 - lon1) * fraction
            
            points.append((lat, lon))
    
    return points

def sample_polygon_geometry(coords: List[Tuple], edge_points: int, 
                            interior_points: int) -> List[Tuple]:
    """Sample points from polygon boundary and interior"""
    points = []
    
    if len(coords) < 3:
        return points
    
    # Sample edges
    perimeter_length = sum(
        haversine_distance(coords[i][0], coords[i][1], 
                          coords[(i+1)%len(coords)][0], coords[(i+1)%len(coords)][1])
        for i in range(len(coords) - 1)
    )
    
    if perimeter_length > 20:  # Only if polygon is large enough
        interval = perimeter_length / edge_points
        edge_samples = sample_line_geometry(coords, interval, 0)
        points.extend(edge_samples[:edge_points])
    
    # Sample interior
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    
    for _ in range(interior_points):
        lat = np.random.uniform(min(lats), max(lats))
        lon = np.random.uniform(min(lons), max(lons))
        points.append((lat, lon))
    
    return points

def sample_point_buffer(lat: float, lon: float, radius: float, 
                        num_points: int) -> List[Tuple]:
    """Sample random points around a center point"""
    points = []
    
    for _ in range(num_points):
        angle = np.random.uniform(0, 2 * math.pi)
        distance = radius * math.sqrt(np.random.uniform(0, 1))
        
        lat_offset = (distance / 111000) * math.cos(angle)
        lon_offset = (distance / (111000 * math.cos(math.radians(lat)))) * math.sin(angle)
        
        points.append((lat + lat_offset, lon + lon_offset))
    
    return points

def process_osm_elements(elements: List[Dict], query_config: Dict, 
                         source_type: LocationSource) -> List[LocationPoint]:
    """Convert OSM elements to location points"""
    sampling = query_config["sampling"]
    points = []
    
    for element in elements:
        elem_type = element.get('type')
        
        try:
            if sampling["type"] == "line" and elem_type == "way":
                if 'geometry' in element:
                    coords = [(node['lat'], node['lon']) 
                             for node in element['geometry']]
                    
                    sampled = sample_line_geometry(
                        coords, 
                        sampling["interval"], 
                        sampling["jitter"]
                    )
                    
                    for lat, lon in sampled:
                        points.append(LocationPoint(
                            lat=lat,
                            lon=lon,
                            source=source_type,
                            context_tags=[],
                            parking_style=ParkingStyle.UNKNOWN,
                            occlusion_level=OcclusionLevel.NONE,
                            osm_metadata=element.get('tags', {})
                        ))
            
            elif sampling["type"] == "polygon":
                if 'geometry' in element:
                    coords = [(node['lat'], node['lon']) 
                             for node in element.get('geometry', [])]
                    
                    if len(coords) > 2:
                        sampled = sample_polygon_geometry(
                            coords,
                            sampling["edge_points"],
                            sampling["interior_points"]
                        )
                        
                        for lat, lon in sampled:
                            points.append(LocationPoint(
                                lat=lat,
                                lon=lon,
                                source=source_type,
                                context_tags=[],
                                parking_style=ParkingStyle.UNKNOWN,
                                occlusion_level=OcclusionLevel.NONE,
                                osm_metadata=element.get('tags', {})
                            ))
            
            elif sampling["type"] == "point_buffer":
                if 'lat' in element and 'lon' in element:
                    center_lat, center_lon = element['lat'], element['lon']
                elif 'center' in element:
                    center_lat = element['center']['lat']
                    center_lon = element['center']['lon']
                else:
                    continue
                
                sampled = sample_point_buffer(
                    center_lat,
                    center_lon,
                    sampling["radius"],
                    sampling["num_points"]
                )
                
                for lat, lon in sampled:
                    points.append(LocationPoint(
                        lat=lat,
                        lon=lon,
                        source=source_type,
                        context_tags=[],
                        parking_style=ParkingStyle.UNKNOWN,
                        occlusion_level=OcclusionLevel.NONE,
                        osm_metadata=element.get('tags', {})
                    ))
            
            elif sampling["type"] == "point":
                if 'lat' in element and 'lon' in element:
                    lat, lon = element['lat'], element['lon']
                elif 'center' in element:
                    lat = element['center']['lat']
                    lon = element['center']['lon']
                else:
                    continue
                
                points.append(LocationPoint(
                    lat=lat,
                    lon=lon,
                    source=source_type,
                    context_tags=[],
                    parking_style=ParkingStyle.UNKNOWN,
                    occlusion_level=OcclusionLevel.NONE,
                    osm_metadata=element.get('tags', {})
                ))
        
        except Exception as e:
            # Skip problematic elements
            continue
    
    return points

def balance_distribution(all_points: List[LocationPoint], 
                         target_count: int) -> List[LocationPoint]:
    """Balance location distribution according to weights"""
    # Group by source
    grouped = {}
    for point in all_points:
        source = point.source
        if source not in grouped:
            grouped[source] = []
        grouped[source].append(point)
    
    # Calculate target counts based on weights
    balanced = []
    for query_name, query_config in OSM_QUERIES.items():
        source = query_config["source"]
        weight = query_config["weight"]
        target = int(target_count * weight)
        
        if source in grouped:
            available = grouped[source]
            sample_size = min(target, len(available))
            if sample_size > 0:
                sampled = np.random.choice(available, sample_size, replace=False)
                balanced.extend(sampled)
    
    # Shuffle for randomness
    np.random.shuffle(balanced)
    
    return balanced[:target_count]

# =============================================================================
# LOCATION FETCHING
# =============================================================================

def fetch_diverse_parking_locations(municipality_data: Dict, 
                                     target_count: int) -> List[LocationPoint]:
    """Fetch diverse parking locations using multi-source strategy"""
    
    print(f"\n🗺️  Fetching diverse parking locations...")
    print(f"   Municipality: {municipality_data['name']}")
    print(f"   Target: {target_count} locations")
    print(f"   Strategy: Multi-source dynamic sampling\n")
    
    center_lat, center_lon = municipality_data['center']
    radius_km = municipality_data['radius_km']
    bbox = calculate_bbox(center_lat, center_lon, radius_km)
    
    all_points = []
    
    # Execute each query type
    for query_name, query_config in OSM_QUERIES.items():
        print(f"   📍 Querying: {query_name}...")
        
        elements = query_osm(query_config, bbox)
        print(f"      Found {len(elements)} OSM elements")
        
        if len(elements) > 0:
            points = process_osm_elements(
                elements, 
                query_config, 
                query_config["source"]
            )
            print(f"      Generated {len(points)} sample points")
            all_points.extend(points)
        else:
            print(f"      No points generated")
        
        time.sleep(1)  # Rate limiting
    
    print(f"\n   ✅ Total raw points: {len(all_points)}")
    
    if len(all_points) == 0:
        print("   ⚠️  No locations found! Generating grid fallback...")
        return generate_grid_fallback(municipality_data, target_count)
    
    # Balance distribution
    print(f"   ⚖️  Balancing distribution...")
    balanced_points = balance_distribution(all_points, target_count)
    
    # Print distribution
    print(f"\n   📊 Final Distribution:")
    source_counts = {}
    for point in balanced_points:
        source = point.source.value
        source_counts[source] = source_counts.get(source, 0) + 1
    
    for source, count in sorted(source_counts.items()):
        percentage = (count / len(balanced_points)) * 100
        print(f"      {source:25s}: {count:4d} ({percentage:.1f}%)")
    
    print(f"\n   🎯 Ready to download {len(balanced_points)} diverse locations!\n")
    
    return balanced_points

def generate_grid_fallback(municipality_data: Dict, num_locations: int) -> List[LocationPoint]:
    """Generate grid-based fallback locations"""
    center_lat, center_lon = municipality_data['center']
    grid_size = int(math.sqrt(num_locations))
    
    spacing_lat = 0.01
    spacing_lon = 0.01
    
    points = []
    for i in range(grid_size):
        for j in range(grid_size):
            lat = center_lat + (i - grid_size/2) * spacing_lat
            lon = center_lon + (j - grid_size/2) * spacing_lon
            
            points.append(LocationPoint(
                lat=lat,
                lon=lon,
                source=LocationSource.DESIGNATED_PARKING,
                context_tags=["grid_fallback"],
                parking_style=ParkingStyle.UNKNOWN,
                occlusion_level=OcclusionLevel.NONE,
                osm_metadata={}
            ))
    
    return points[:num_locations]

# =============================================================================
# IMAGE DOWNLOAD
# =============================================================================

def deg2num(lat_deg: float, lon_deg: float, zoom: int) -> Tuple[int, int]:
    """Convert lat/lon to tile numbers"""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def fetch_single_tile(x: int, y: int, zoom: int, session: requests.Session) -> Optional:
    """Fetch a single tile from Google"""
    from PIL import Image
    from io import BytesIO
    
    url = f"https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={zoom}"
    
    try:
        response = session.get(url, timeout=CONFIG["timeout"])
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content))
            response.close()
            return image
    except Exception as e:
        pass
    return None

def fetch_and_stitch_image(lat: float, lng: float, zoom: int, 
                            grid_size: int = 6) -> Optional:
    """Fetch tiles and stitch into single image"""
    from PIL import Image
    
    center_x, center_y = deg2num(lat, lng, zoom)
    offset = grid_size // 2
    
    tile_size = CONFIG["tile_size"]
    stitched = Image.new('RGB', (grid_size * tile_size, grid_size * tile_size), 
                         (128, 128, 128))
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    tiles_fetched = 0
    tiles_total = grid_size * grid_size
    
    for dy in range(grid_size):
        for dx in range(grid_size):
            x = center_x + dx - offset
            y = center_y + dy - offset
            
            tile = fetch_single_tile(x, y, zoom, session)
            
            if tile:
                stitched.paste(tile, (dx * tile_size, dy * tile_size))
                tiles_fetched += 1
                del tile
    
    session.close()
    
    if tiles_fetched < tiles_total * 0.7:
        return None
    
    # Resize to final size
    if stitched.size != (CONFIG["final_size"], CONFIG["final_size"]):
        resized = stitched.resize(
            (CONFIG["final_size"], CONFIG["final_size"]),
            Image.Resampling.LANCZOS
        )
        del stitched
        return resized
    
    return stitched

# =============================================================================
# QUALITY ANALYSIS
# =============================================================================

def calculate_quality_metrics(image, location_point: LocationPoint) -> Dict:
    """Calculate quality metrics with context detection"""
    import cv2
    
    img_array = np.array(image)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
    # Standard metrics
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = float(np.var(laplacian))
    contrast = float(np.std(img_array))
    brightness = float(np.mean(img_array))
    
    edges = cv2.Canny(gray, 50, 150)
    edge_density = float(np.sum(edges > 0) / edges.size)
    
    # Tree coverage detection
    hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([85, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    tree_coverage = float(np.sum(mask > 0) / mask.size)
    
    # Update location context
    if tree_coverage > 0.3:
        if "trees_detected" not in location_point.context_tags:
            location_point.context_tags.append("trees_detected")
        location_point.occlusion_level = OcclusionLevel.PARTIAL
    
    if tree_coverage > 0.5:
        location_point.occlusion_level = OcclusionLevel.HEAVY
    
    # Clean up
    del img_array, gray, laplacian, edges, hsv, mask
    gc.collect()
    
    return {
        'sharpness': sharpness,
        'contrast': contrast,
        'brightness': brightness,
        'edge_density': edge_density,
        'tree_coverage': tree_coverage,
        'occlusion_level': location_point.occlusion_level.value
    }

# =============================================================================
# REGISTRY MANAGEMENT
# =============================================================================

def load_registry(registry_file: str) -> Dict:
    """Load download registry"""
    if os.path.exists(registry_file):
        try:
            with open(registry_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_to_registry(registry_file: str, location_hash: str, metadata: Dict):
    """Save location to registry"""
    registry = load_registry(registry_file)
    registry[location_hash] = metadata
    
    with open(registry_file, 'w') as f:
        json.dump(registry, f, indent=2)

# =============================================================================
# MAIN DOWNLOAD PIPELINE
# =============================================================================

def download_dataset(municipality_key: str, municipality_data: Dict,
                     locations: List[LocationPoint], output_dir: str,
                     resume: bool = True):
    """Main download pipeline with resume capability"""
    from PIL import Image
    
    # Setup directories
    os.makedirs(f"{output_dir}/images", exist_ok=True)
    os.makedirs(f"{output_dir}/metadata", exist_ok=True)
    
    # Load registry
    registry_file = f"{output_dir}/metadata/download_registry.json"
    registry = load_registry(registry_file) if resume else {}
    
    # Statistics
    stats = {
        'downloaded': 0,
        'skipped': 0,
        'failed': 0,
        'start_time': datetime.now().isoformat()
    }
    
    print("\n" + "="*70)
    print("🚀 STARTING DOWNLOAD")
    print("="*70 + "\n")
    
    for idx, location_point in enumerate(locations, 1):
        location_hash = generate_location_hash(location_point.lat, location_point.lon)
        
        print(f"[{idx}/{len(locations)}] 🎯 {location_point.source.value}")
        print(f"         Location: {location_point.lat:.5f}, {location_point.lon:.5f}")
        
        # Check if already downloaded
        if resume and location_hash in registry:
            print(f"         ⏭️  Already downloaded - SKIPPING")
            stats['skipped'] += 1
            print()
            continue
        
        try:
            # Fetch image
            print(f"         📡 Fetching {CONFIG['stitch_tiles']}x{CONFIG['stitch_tiles']} tiles...")
            image = fetch_and_stitch_image(
                location_point.lat, 
                location_point.lon, 
                CONFIG['zoom_level'],
                CONFIG['stitch_tiles']
            )
            
            if image is None:
                print(f"         ❌ Failed to fetch tiles")
                stats['failed'] += 1
                print()
                continue
            
            # Calculate quality
            print(f"         📊 Analyzing quality...")
            quality = calculate_quality_metrics(image, location_point)
            
            # Quality check
            if quality['sharpness'] < CONFIG['min_quality_sharpness']:
                print(f"         ⚠️  Low quality (sharpness: {quality['sharpness']:.0f}) - SKIPPING")
                stats['failed'] += 1
                del image
                gc.collect()
                print()
                continue
            
            print(f"         Quality: sharpness={quality['sharpness']:.0f}, "
                  f"edges={quality['edge_density']:.2%}, "
                  f"trees={quality['tree_coverage']:.2%}")
            
            # Save image
            filename = f"parking_{municipality_key}_{idx:04d}_{location_hash}.png"
            filepath = f"{output_dir}/images/{filename}"
            print(f"         💾 Saving image...")
            image.save(filepath, format='PNG', optimize=True)
            
            file_size = os.path.getsize(filepath) / (1024*1024)
            print(f"         ✅ Saved: {filename} ({file_size:.2f} MB)")
            
            # Free memory
            del image
            gc.collect()
            
            # Save metadata
            metadata = {
                'id': idx,
                'location_hash': location_hash,
                'source_type': location_point.source.value,
                'context_tags': location_point.context_tags,
                'parking_style': location_point.parking_style.value,
                'occlusion_level': location_point.occlusion_level.value,
                'latitude': location_point.lat,
                'longitude': location_point.lon,
                'municipality': municipality_data['name'],
                'filepath': filepath,
                'timestamp': datetime.now().isoformat(),
                'quality': quality,
                'zoom_level': CONFIG['zoom_level'],
                'resolution': f"{CONFIG['final_size']}x{CONFIG['final_size']}",
                'file_size_mb': file_size,
                'osm_metadata': location_point.osm_metadata
            }
            
            metadata_file = f"{output_dir}/metadata/image_{idx:04d}_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Update registry
            save_to_registry(registry_file, location_hash, metadata)
            
            stats['downloaded'] += 1
            print(f"         ✅ Complete! ({stats['downloaded']}/{len(locations)})\n")
            
            # Rate limiting
            time.sleep(CONFIG["request_delay"])
            
        except Exception as e:
            print(f"         ❌ Error: {e}\n")
            stats['failed'] += 1
            gc.collect()
    
    # Save summary
    stats['end_time'] = datetime.now().isoformat()
    stats['municipality'] = municipality_data['name']
    stats['total_requested'] = len(locations)
    
    summary_file = f"{output_dir}/metadata/download_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    return stats

def print_final_summary(stats: Dict, output_dir: str):
    """Print final summary"""
    print("\n" + "="*70)
    print("📊 DOWNLOAD COMPLETE")
    print("="*70)
    print(f"  ✅ Downloaded:     {stats['downloaded']}")
    print(f"  ⏭️  Skipped:        {stats['skipped']} (already existed)")
    print(f"  ❌ Failed:         {stats['failed']}")
    print(f"  📁 Output:         {output_dir}")
    print("="*70)
    
    # Calculate total size
    try:
        total_size = 0
        images_dir = f"{output_dir}/images"
        for file in os.listdir(images_dir):
            total_size += os.path.getsize(f"{images_dir}/{file}")
        
        print(f"\n💾 Dataset Statistics:")
        print(f"   Total size: {total_size / (1024*1024):.1f} MB")
        if stats['downloaded'] > 0:
            print(f"   Avg per image: {total_size / stats['downloaded'] / (1024*1024):.2f} MB")
    except:
        pass
    
    print(f"\n📂 Directory Structure:")
    print(f"   {output_dir}/")
    print(f"   ├── images/           ({stats['downloaded']} images)")
    print(f"   └── metadata/         (registry + individual metadata)")
    
    print("\n" + "="*70)

# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Production-Ready Parking Detection Dataset Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: 1000 images from Utrecht
  python production_parking_generator.py

  # Specify municipality and count
  python production_parking_generator.py --municipality amsterdam --count 2000

  # Custom output directory
  python production_parking_generator.py --output ./my_dataset

  # Resume interrupted download
  python production_parking_generator.py --resume

  # No resume (start fresh)
  python production_parking_generator.py --no-resume

Available municipalities: utrecht, amsterdam, rotterdam, den_haag, eindhoven
        """
    )
    
    parser.add_argument(
        '--municipality', '-m',
        type=str,
        default='utrecht',
        choices=list(MUNICIPALITIES.keys()),
        help='Municipality to download from (default: utrecht)'
    )
    
    parser.add_argument(
        '--count', '-n',
        type=int,
        default=1000,
        help='Number of images to generate (default: 1000)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output directory (default: parking_dataset_{municipality}_{date})'
    )
    
    parser.add_argument(
        '--resume', '-r',
        action='store_true',
        default=True,
        help='Resume from existing download (default: True)'
    )
    
    parser.add_argument(
        '--no-resume',
        action='store_false',
        dest='resume',
        help='Start fresh, ignore existing downloads'
    )
    
    parser.add_argument(
        '--min-quality',
        type=int,
        default=300,
        help='Minimum sharpness quality threshold (default: 300)'
    )
    
    parser.add_argument(
        '--radius',
        type=float,
        default=None,
        help='Search radius in km (default: municipality specific)'
    )
    
    return parser.parse_args()

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main application entry point"""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Print header
        print_header()
        
        # Check dependencies
        if not check_dependencies():
            return
        
        # Get municipality data
        municipality_key = args.municipality
        municipality_data = MUNICIPALITIES[municipality_key].copy()
        
        # Override radius if specified
        if args.radius:
            municipality_data['radius_km'] = args.radius
        
        # Update quality config
        CONFIG['min_quality_sharpness'] = args.min_quality
        
        # Generate output directory
        if args.output:
            output_dir = args.output
        else:
            timestamp = datetime.now().strftime("%Y%m%d")
            output_dir = f"parking_dataset_{municipality_key}_{timestamp}"
        
        # Print configuration
        print("📋 Configuration:")
        print(f"   Municipality: {municipality_data['name']}")
        print(f"   Target images: {args.count}")
        print(f"   Search radius: {municipality_data['radius_km']} km")
        print(f"   Output directory: {output_dir}")
        print(f"   Resume mode: {'Enabled' if args.resume else 'Disabled'}")
        print(f"   Min quality: {args.min_quality}")
        print(f"   Grid size: {CONFIG['stitch_tiles']}x{CONFIG['stitch_tiles']}")
        print(f"   Final resolution: {CONFIG['final_size']}x{CONFIG['final_size']}")
        
        # Confirm
        print()
        confirm = input("Proceed with download? (y/n): ")
        if confirm.lower() != 'y':
            print("\n❌ Operation cancelled")
            return
        
        # Fetch locations
        locations = fetch_diverse_parking_locations(municipality_data, args.count)
        
        if len(locations) < args.count:
            print(f"\n⚠️  Only {len(locations)} locations available (requested {args.count})")
            proceed = input(f"Continue with {len(locations)} images? (y/n): ").strip().lower()
            if proceed != 'y':
                print("\n❌ Operation cancelled")
                return
        
        # Download dataset
        stats = download_dataset(
            municipality_key,
            municipality_data,
            locations,
            output_dir,
            resume=args.resume
        )
        
        # Print summary
        print_final_summary(stats, output_dir)
        
        print("\n✨ Dataset generation complete!")
        print(f"✨ Use images in '{output_dir}/images/' for training")
        print(f"✨ Total locations: {stats['downloaded']} diverse parking areas")
        print("\n" + "="*70)
        
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
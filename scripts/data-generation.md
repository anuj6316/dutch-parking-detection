# Production Parking Dataset Generator - Usage Guide

## 🎯 Overview

Production-ready parking detection dataset generator with dynamic multi-source location fetching. Generates diverse, real-world parking scenarios for ML training.

**Key Features:**
- ✅ 6x6 tile grid, 1536x1536 resolution
- ✅ Multi-source OSM queries (40% street, 30% residential, 20% commercial, 10% designated)
- ✅ Resume capability with duplicate detection
- ✅ Enhanced metadata with context detection
- ✅ No visualization directory (space efficient)
- ✅ Quality filtering and validation
- ✅ Command-line arguments support
- ✅ Default: 1000 images from Utrecht

---

## 📦 Installation

### Prerequisites

Python 3.7+ required. The script will auto-install dependencies if missing:
- requests
- pillow
- numpy
- opencv-python

### Quick Start

```bash
# Download the script
# Make it executable
chmod +x production_parking_generator.py

# Run with defaults (1000 images from Utrecht)
python3 production_parking_generator.py
```

The script will check dependencies and prompt to install if needed.

---

## 🚀 Usage

### Basic Usage

```bash
# Default: 1000 images from Utrecht
python3 production_parking_generator.py

# Specify different municipality
python3 production_parking_generator.py --municipality amsterdam

# Specify number of images
python3 production_parking_generator.py --count 2000

# Custom output directory
python3 production_parking_generator.py --output ./my_parking_dataset
```

### Command Line Arguments

```
Options:
  -h, --help            Show help message and exit
  
  -m, --municipality    Municipality to download from
                        Choices: utrecht, amsterdam, rotterdam, den_haag, eindhoven
                        Default: utrecht
  
  -n, --count          Number of images to generate
                        Default: 1000
  
  -o, --output         Output directory path
                        Default: parking_dataset_{municipality}_{date}
  
  -r, --resume         Resume from existing download (default behavior)
  
  --no-resume          Start fresh, ignore existing downloads
  
  --min-quality        Minimum sharpness quality threshold
                        Default: 300
  
  --radius             Search radius in km
                        Default: municipality specific (10-15 km)
```

### Examples

#### 1. Default Run (Utrecht, 1000 images)
```bash
python3 production_parking_generator.py
```
Output: `parking_dataset_utrecht_20260129/`

#### 2. Amsterdam with 2000 images
```bash
python3 production_parking_generator.py \
  --municipality amsterdam \
  --count 2000
```
Output: `parking_dataset_amsterdam_20260129/`

#### 3. Custom output directory
```bash
python3 production_parking_generator.py \
  --municipality rotterdam \
  --count 1500 \
  --output ./rotterdam_parking_v1
```
Output: `./rotterdam_parking_v1/`

#### 4. Resume interrupted download
```bash
# First run (interrupted)
python3 production_parking_generator.py --count 2000
# ... interrupted after 500 images ...

# Resume automatically (default behavior)
python3 production_parking_generator.py --count 2000
# Will skip the 500 already downloaded, continue from 501
```

#### 5. Start fresh (no resume)
```bash
python3 production_parking_generator.py \
  --no-resume \
  --count 1000
```

#### 6. Higher quality threshold
```bash
python3 production_parking_generator.py \
  --min-quality 500 \
  --count 1000
# Will only keep images with sharpness > 500
```

#### 7. Larger search radius
```bash
python3 production_parking_generator.py \
  --municipality utrecht \
  --radius 20 \
  --count 3000
# Search 20km radius instead of default 12km
```

---

## 📂 Output Structure

```
parking_dataset_utrecht_20260129/
│
├── images/
│   ├── parking_utrecht_0001_a3f2b8c9.png    (1536x1536, ~4-5 MB)
│   ├── parking_utrecht_0002_d4e1c7f3.png
│   ├── parking_utrecht_0003_8b9a2e4f.png
│   └── ... (up to 1000 images)
│
└── metadata/
    ├── download_registry.json               (duplicate prevention)
    ├── download_summary.json                (statistics)
    ├── image_0001_metadata.json
    ├── image_0002_metadata.json
    ├── image_0003_metadata.json
    └── ... (individual metadata per image)
```

### No Visualization Directory
Unlike previous versions, this script does NOT create a `visualizations/` directory to save disk space.

---

## 📊 Expected Distribution

The script automatically balances location sources:

```
Distribution:
├── Street Parking: 40%
│   ├── Residential streets: 25%
│   ├── Service roads: 10%
│   └── Tertiary roads: 5%
│
├── Residential Areas: 30%
│   ├── Residential zones: 20%
│   └── Apartments: 10%
│
├── Commercial: 20%
│   ├── Retail: 10%
│   └── Commercial zones: 10%
│
└── Designated Parking: 10%
```

---

## 🔍 Metadata Format

Each image has two metadata files:

### 1. Individual Metadata (`image_0001_metadata.json`)

```json
{
  "id": 1,
  "location_hash": "a3f2b8c9",
  "source_type": "residential_street",
  "context_tags": ["trees_detected"],
  "parking_style": "parallel",
  "occlusion_level": "partial",
  "latitude": 52.09234,
  "longitude": 5.08765,
  "municipality": "Utrecht",
  "filepath": "parking_dataset_utrecht_20260129/images/parking_utrecht_0001_a3f2b8c9.png",
  "timestamp": "2026-01-29T10:30:45.123456",
  "quality": {
    "sharpness": 456.7,
    "contrast": 45.3,
    "brightness": 128.4,
    "edge_density": 0.12,
    "tree_coverage": 0.35,
    "occlusion_level": "partial"
  },
  "zoom_level": 21,
  "resolution": "1536x1536",
  "file_size_mb": 4.23,
  "osm_metadata": {
    "highway": "residential",
    "name": "Hoofdstraat"
  }
}
```

### 2. Registry (`download_registry.json`)

Maps location hashes to metadata (prevents duplicates):

```json
{
  "a3f2b8c9": { ... metadata ... },
  "d4e1c7f3": { ... metadata ... },
  "8b9a2e4f": { ... metadata ... }
}
```

### 3. Summary (`download_summary.json`)

```json
{
  "downloaded": 987,
  "skipped": 13,
  "failed": 0,
  "start_time": "2026-01-29T10:00:00",
  "end_time": "2026-01-29T12:30:00",
  "municipality": "Utrecht",
  "total_requested": 1000
}
```

---

## ⚙️ Configuration

### Default Configuration

```python
CONFIG = {
    "zoom_level": 21,           # ~0.15m per pixel
    "stitch_tiles": 6,          # 6x6 grid
    "tile_size": 256,           # 256px per tile
    "final_size": 1536,         # 1536x1536 final image
    "request_delay": 0.5,       # 0.5s between requests
    "timeout": 15,              # 15s request timeout
    "retry_attempts": 3,        # 3 retry attempts
    "min_quality_sharpness": 300,  # Minimum quality
}
```

### Adjusting Distribution Weights

Edit the script's `OSM_QUERIES` dictionary to change distribution:

```python
# Example: More street parking, less designated
"residential_streets": { "weight": 0.35 },  # Increase from 0.25
"designated_parking": { "weight": 0.05 },   # Decrease from 0.10
```

### Available Municipalities

```python
MUNICIPALITIES = {
    "utrecht": {
        "center": (52.092876, 5.092312),
        "radius_km": 12,
    },
    "amsterdam": {
        "center": (52.3676, 4.9041),
        "radius_km": 15,
    },
    "rotterdam": {
        "center": (51.9225, 4.47917),
        "radius_km": 14,
    },
    "den_haag": {
        "center": (52.0705, 4.3007),
        "radius_km": 12,
    },
    "eindhoven": {
        "center": (51.4416, 5.4697),
        "radius_km": 10,
    },
}
```

To add more cities, edit this dictionary in the script.

---

## 🔧 Troubleshooting

### Issue: "No locations found"

**Cause:** OSM query timeout or no data in area  
**Solution:**
```bash
# Increase radius
python3 production_parking_generator.py --radius 20

# Or use different municipality
python3 production_parking_generator.py --municipality amsterdam
```

### Issue: "Too many failed downloads"

**Cause:** Network issues or rate limiting  
**Solution:**
```bash
# Edit CONFIG in script:
CONFIG = {
    "request_delay": 1.0,  # Increase from 0.5 to 1.0
    "timeout": 30,         # Increase from 15 to 30
}
```

### Issue: "All images low quality"

**Cause:** Area has poor satellite coverage  
**Solution:**
```bash
# Lower quality threshold
python3 production_parking_generator.py --min-quality 200

# Or try different area
python3 production_parking_generator.py --municipality rotterdam
```

### Issue: "Out of memory"

**Cause:** Processing too many images  
**Solution:**
The script already uses memory-efficient processing (one tile at a time). If still happening:
- Close other applications
- Process in smaller batches (e.g., 500 at a time)

### Issue: "Resume not working"

**Cause:** Registry file corrupted or missing  
**Solution:**
```bash
# Check registry exists
ls parking_dataset_*/metadata/download_registry.json

# If corrupted, delete and start fresh
rm parking_dataset_*/metadata/download_registry.json
python3 production_parking_generator.py --count 1000
```

---

## 📈 Performance

### Speed

```
Single image download time: ~45-60 seconds
├── Tile fetching: ~30-40s (36 tiles)
├── Quality analysis: ~5-8s
├── Saving: ~2-3s
└── Metadata: ~1s

Full dataset (1000 images):
├── Estimated time: 12-15 hours
├── Network usage: ~10-12 GB
└── Disk usage: ~4-5 GB
```

### Optimization Tips

1. **Run overnight:** Downloads take several hours
2. **Stable internet:** Use wired connection if possible
3. **Resume capability:** Don't worry about interruptions
4. **Batch processing:** Download in chunks of 500-1000

---

## 🎓 Training Pipeline Integration

### Step 1: Generate Dataset

```bash
# Generate 2000 diverse images
python3 production_parking_generator.py \
  --municipality utrecht \
  --count 2000 \
  --output ./training_data
```

### Step 2: Analyze Distribution

```python
import json
import pandas as pd

# Load all metadata
metadata_list = []
for i in range(1, 2001):
    with open(f'./training_data/metadata/image_{i:04d}_metadata.json') as f:
        metadata_list.append(json.load(f))

df = pd.DataFrame(metadata_list)

# Check distribution
print(df['source_type'].value_counts(normalize=True))
print(df['occlusion_level'].value_counts(normalize=True))
print(df['parking_style'].value_counts(normalize=True))
```

### Step 3: Filter by Context

```python
# Get only street parking images
street_images = df[df['source_type'].str.contains('street')]
print(f"Street parking: {len(street_images)} images")

# Get tree-covered images
tree_images = df[df['quality'].apply(lambda x: x['tree_coverage'] > 0.3)]
print(f"Tree-covered: {len(tree_images)} images")

# Get high-quality images
high_quality = df[df['quality'].apply(lambda x: x['sharpness'] > 500)]
print(f"High quality: {len(high_quality)} images")
```

### Step 4: Train Model

```python
# Example with YOLOv8
from ultralytics import YOLO

# Prepare dataset
image_paths = df['filepath'].tolist()

# Train
model = YOLO('yolov8n.pt')
results = model.train(
    data='parking_dataset.yaml',
    epochs=100,
    imgsz=1536,
    batch=8
)
```

---

## 🔍 Quality Validation

### Manual Check

```bash
# View random sample
import random
from PIL import Image

metadata_files = glob.glob('parking_dataset_*/metadata/image_*_metadata.json')
sample = random.sample(metadata_files, 10)

for meta_file in sample:
    with open(meta_file) as f:
        meta = json.load(f)
    
    print(f"Source: {meta['source_type']}")
    print(f"Quality: {meta['quality']['sharpness']:.0f}")
    print(f"Trees: {meta['quality']['tree_coverage']:.2%}")
    
    img = Image.open(meta['filepath'])
    img.show()
    input("Press Enter for next...")
```

### Automated Validation

```python
def validate_dataset(metadata_dir):
    """Validate dataset meets quality standards"""
    
    checks = {
        "street_parking_min": 0.35,    # At least 35% street
        "tree_coverage_min": 0.20,     # At least 20% with trees
        "min_quality": 300,            # Minimum sharpness
        "diversity_min": 4             # At least 4 source types
    }
    
    # Load metadata
    metadata_list = []
    for file in glob.glob(f'{metadata_dir}/image_*_metadata.json'):
        with open(file) as f:
            metadata_list.append(json.load(f))
    
    # Calculate metrics
    total = len(metadata_list)
    street_count = sum(1 for m in metadata_list if 'street' in m['source_type'])
    tree_count = sum(1 for m in metadata_list if m['quality']['tree_coverage'] > 0.2)
    low_quality = sum(1 for m in metadata_list if m['quality']['sharpness'] < checks['min_quality'])
    source_types = len(set(m['source_type'] for m in metadata_list))
    
    # Validate
    results = {
        "total_images": total,
        "street_parking_ratio": street_count / total,
        "tree_coverage_ratio": tree_count / total,
        "low_quality_count": low_quality,
        "source_diversity": source_types,
        "passed": True
    }
    
    if results["street_parking_ratio"] < checks["street_parking_min"]:
        results["passed"] = False
        print(f"❌ Insufficient street parking: {results['street_parking_ratio']:.1%}")
    
    if results["tree_coverage_ratio"] < checks["tree_coverage_min"]:
        results["passed"] = False
        print(f"❌ Insufficient tree coverage: {results['tree_coverage_ratio']:.1%}")
    
    if results["source_diversity"] < checks["diversity_min"]:
        results["passed"] = False
        print(f"❌ Insufficient diversity: {results['source_diversity']} types")
    
    if results["passed"]:
        print("✅ Dataset validation passed!")
    
    return results
```

---

## 📝 Best Practices

### 1. Start Small
```bash
# Test with 100 images first
python3 production_parking_generator.py --count 100
# Verify quality and distribution
# Then scale up to 1000+
```

### 2. Use Resume
```bash
# Always use resume for large datasets
python3 production_parking_generator.py --count 2000 --resume
# If interrupted, just run again - it will continue
```

### 3. Monitor Progress
```bash
# Watch output directory size
watch -n 10 'du -sh parking_dataset_*'

# Count downloaded images
watch -n 10 'ls parking_dataset_*/images/ | wc -l'
```

### 4. Validate After Download
```python
# Check distribution
python3 -c "
import json
import glob
from collections import Counter

files = glob.glob('parking_dataset_*/metadata/image_*_metadata.json')
sources = []
for f in files:
    with open(f) as fp:
        sources.append(json.load(fp)['source_type'])

for source, count in Counter(sources).most_common():
    print(f'{source:30s}: {count:4d} ({count/len(sources)*100:.1f}%)')
"
```

### 5. Backup Metadata
```bash
# Metadata is small but valuable
tar -czf metadata_backup.tar.gz parking_dataset_*/metadata/
```

---

## 🚨 Important Notes

1. **Network Required:** Continuous internet connection needed
2. **Disk Space:** Plan for ~4-5 MB per image (5 GB for 1000 images)
3. **Time:** Allow 12-15 hours for 1000 images
4. **Rate Limiting:** Script includes delays to avoid bans
5. **Quality:** Not all locations have good satellite coverage
6. **Resume:** Always safe to Ctrl+C and resume later

---

## 📞 Support

If you encounter issues:

1. Check this README's Troubleshooting section
2. Verify internet connection and disk space
3. Try different municipality or smaller count
4. Check metadata files for clues about failures

---

## 🎯 Summary

```bash
# Quick start (default)
python3 production_parking_generator.py

# Production run (Amsterdam, 2000 images)
python3 production_parking_generator.py \
  --municipality amsterdam \
  --count 2000 \
  --output ./production_dataset_v1

# Result:
# ├── 2000 diverse parking images (1536x1536)
# ├── 40% street parking
# ├── 30% residential
# ├── 20% commercial
# └── 10% designated lots
```

**Your model will learn from real-world scenarios!** 🚀
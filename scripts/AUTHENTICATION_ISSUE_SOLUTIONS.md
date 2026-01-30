# ⚠️ Label Studio Import Issue - Authentication Required

## Problem

Label Studio requires authentication to access images, and both external HTTP URLs and API calls are returning **401 Unauthorized** errors.

**Error Details:**
- Status Code: 401
- Message: "Authentication credentials were not provided"
- Occurs with: HTTP URLs (`http://172.16.20.161:8080/...`) and API requests

---

## Root Cause

Label Studio's local file serving (`LOCAL_FILES_SERVING_ENABLED=true`) still requires authentication for HTTP requests, even from within the Label Studio UI itself. This is a known limitation when using local file serving.

---

## Solutions

### Option 1: Manual Import (RECOMMENDED)

This is the most reliable approach:

**Step 1: Open Label Studio**
```
URL: http://localhost:8080
Login: admin / admin
```

**Step 2: Upload Images via UI**
1. Click "Import" → "Upload files"
2. Select all 216 images from: `dataset/dataset-for-viz/images/`
3. Click "Upload"
4. Wait for upload to complete

**Step 3: Configure Labeling Interface**
1. Go to Settings → Labeling Interface
2. Copy from `scripts/labelstudio-config.xml`:
```xml
<View>
  <Image name="image" value="$image" zoom="true" zoomControl="true"/>
  <PolygonLabels name="label" toName="image" fillOpacity="0.2" strokeWidth="3">
    <Label value="Parking" background="green"/>
  </PolygonLabels>
</View>
```
3. Paste and click "Save"

**Step 4: Import Annotations Separately**
Since we can't import both images and annotations together:
1. Export annotations from `scripts/labelstudio-import.json`
2. Convert to CSV format that Label Studio accepts
3. Or manually adjust polygons after importing images

---

### Option 2: Use Cloud Storage (Recommended for Production)

Upload images to cloud storage (S3, GCS, Azure) and connect Label Studio to it via:
1. Settings → Cloud Storage
2. Configure cloud bucket with proper CORS
3. Import JSON tasks with cloud URLs

**Pros:**
- ✅ No authentication issues
- ✅ Scales to large datasets
- ✅ Works across multiple Label Studio instances

**Cons:**
- ❌ Requires cloud storage setup
- ❌ Additional costs

---

### Option 3: Configure Label Studio for Public Access

Modify docker-compose to allow unauthenticated access:

**Add to `scripts/lable-studio.yml`:**
```yaml
environment:
  - LOCAL_FILES_SERVING_ENABLED=true
  - LOCAL_FILES_DOCUMENT_ROOT=/label-studio/data/media
  - LABEL_STUDIO_DISABLE_SIGNUP=true
  - LABEL_STUDIO_USERNAME=admin
  - LABEL_STUDIO_PASSWORD=admin
  - DJANGO_ALLOW_UNSAFE_INLINE_MARKDOWN=true
  - LABEL_STUDIO_ALLOW_UNSAFE_INLINE_MARKDOWN=true
```

**Restart container:**
```bash
docker-compose -f scripts/lable-studio.yml down
docker-compose -f scripts/lable-studio.yml up -d
```

**Note:** This may not fully resolve the issue as authentication is enforced at the application level.

---

### Option 4: Use Label Studio's Direct File Upload

Instead of referencing images via URLs, we can base64-encode images and include them directly in the JSON:

**Script to create base64 JSON:**
```python
#!/usr/bin/env python3
import json
import base64
from pathlib import Path

def create_base64_tasks():
    tasks = []
    
    for img_file in Path("dataset/dataset-for-viz/images").glob("*.png"):
        label_file = Path("dataset/dataset-for-viz/labels") / f"{img_file.stem}.txt"
        
        if not label_file.exists():
            continue
        
        # Read and encode image
        with open(img_file, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode()
        
        # Create task with embedded image
        task = {
            "data": {
                "image": f"data:image/png;base64,{img_data}"
            }
        }
        tasks.append(task)
    
    # Save
    with open("scripts/labelstudio-base64-tasks.json", 'w') as f:
        json.dump(tasks, f)
    
    print(f"Created {len(tasks)} tasks with base64-encoded images")

if __name__ == "__main__":
    create_base64_tasks()
```

**Note:** This approach will create a very large JSON file (~600MB+), which may hit import size limits.

---

## Current Status

✅ **Images Copied to Container:** 216 images in `/label-studio/data/media/upload/dataset-for-viz/`
✅ **JSON Created:** `scripts/labelstudio-import.json` (195 tasks with polygon annotations)
✅ **Labeling Config:** `scripts/labelstudio-config.xml` ready
❌ **API Authentication:** Failing due to Label Studio auth requirements
❌ **HTTP URL Access:** Failing due to auth requirements (401 errors)

---

## Recommended Next Steps

### For Immediate Use:
**Manual UI Import** (Option 1):
1. Upload 216 images via Label Studio UI
2. Configure labeling interface
3. Manually adjust polygons based on visual reference

### For Production/Scale:
**Cloud Storage** (Option 2):
1. Set up S3/GCS bucket
2. Upload images
3. Configure Label Studio cloud storage
4. Import JSON with cloud URLs

---

## Files Available

| File | Purpose | Status |
|------|---------|--------|
| `scripts/labelstudio-config.xml` | Labeling interface | ✅ Ready |
| `scripts/labelstudio-import.json` | Tasks (relative URLs) | ⚠️ Won't work directly |
| `scripts/labelstudio-import-fixed.json` | Tasks (HTTP URLs) | ❌ 401 errors |
| `scripts/labelstudio-import-relative.json` | Tasks (relative paths) | ⚠️ May not work |
| `dataset/dataset-for-viz/images/` | Source images | ✅ 216 files |
| `dataset/dataset-for-viz/labels/` | Source labels | ✅ 216 files |

---

## Technical Details

**Issue:** Label Studio enforces authentication on all file access, including local file serving.

**Authentication Flow:**
1. User logs in → Gets session cookie/token
2. UI makes requests to Label Studio API → Uses session auth
3. UI tries to load image URLs → **Doesn't include session auth** → 401 error

**Why It Fails:**
- HTML `<img>` tags don't automatically send authentication headers
- Label Studio doesn't inject auth into image URL requests
- External HTTP requests from the browser context don't have the session

---

## Conclusion

The dataset is **ready for annotation** but requires a different import strategy than initially planned.

**Best approaches:**
1. **Manual upload** (immediate, reliable)
2. **Cloud storage** (scalable, production-ready)
3. **Modify Label Studio config** (complex, may not resolve)

**Files are prepared:** All scripts, configs, and JSON files are ready in `scripts/` directory.

---

**Next:** Decide on import approach and proceed accordingly.

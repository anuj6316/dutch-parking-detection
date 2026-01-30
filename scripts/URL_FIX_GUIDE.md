# ✅ URL Fixed - Import with Corrected JSON

## Problem Solved

The original JSON used relative paths (`/data/upload/...`) which Label Studio couldn't resolve. I've fixed this by converting all URLs to full HTTP URLs.

---

## Fixed File

**File:** `scripts/labelstudio-import-fixed.json`
- Size: 749 KB
- Total tasks: 195
- URL format: Full HTTP URLs
- Example: `http://172.16.20.161:8080/data/upload/dataset-for-viz/filename.png`

---

## What Was Changed

**Before (Not Working):**
```json
{
  "data": {
    "image": "/data/upload/dataset-for-viz/filename.png"
  }
}
```

**After (Fixed):**
```json
{
  "data": {
    "image": "http://172.16.20.161:8080/data/upload/dataset-for-viz/filename.png"
  }
}
```

---

## Updated Import Instructions

### Step 1: Access Label Studio
**URL:** http://localhost:8080 (or http://172.16.20.161:8080)
- Username: `admin`
- Password: `admin`

### Step 2: Create Project
1. Click "Create Project"
2. Name: `Parking Dataset - 195 Tasks`
3. Click "Create"

### Step 3: Configure Labeling Interface
1. Go to Settings → Labeling Interface
2. Copy from `scripts/labelstudio-config.xml`
3. Paste and click "Save"

```xml
<View>
  <Image name="image" value="$image" zoom="true" zoomControl="true"/>
  <PolygonLabels name="label" toName="image" fillOpacity="0.2" strokeWidth="3">
    <Label value="Parking" background="green"/>
  </PolygonLabels>
</View>
```

### Step 4: Import Tasks
1. Click "Import" → "Upload from file"
2. **Use this file:** `scripts/labelstudio-import-fixed.json` ✅
3. Click "Import Tasks"
4. Wait for import to complete (~1-2 minutes)

### Step 5: Enable Predictions Display
1. Go to Settings → Machine Learning
2. Enable: "Show predictions to annotators in Label Stream and Quick View"
3. Click "Save"

### Step 6: Verify & Start Annotating
1. Open first task from Label Stream
2. **✅ Green polygons should appear now!**
3. Edit polygon points as needed
4. Submit when complete

---

## Why This Works

Label Studio needs full HTTP URLs to access images:
- **Host IP:** 172.16.20.161 (your machine's IP)
- **Port:** 8080 (Label Studio port)
- **Path:** /data/upload/dataset-for-viz/ (internal Label Studio path)

Images are served by Label Studio itself from the `/label-studio/data/media/upload/` directory.

---

## Files Summary

| File | Purpose | Status |
|------|---------|--------|
| `scripts/labelstudio-config.xml` | Labeling interface | ✅ Ready |
| `scripts/labelstudio-import.json` | Original JSON (broken URLs) | ❌ Don't use |
| `scripts/labelstudio-import-fixed.json` | Fixed JSON (working URLs) | ✅ USE THIS |
| `scripts/convert_to_labelstudio.py` | Conversion script | ✅ Created |
| `scripts/fix_labelstudio_urls.py` | URL fixer script | ✅ Created |

---

## Quick Command Reference

**If you need to re-run URL fixing:**
```bash
python3 scripts/fix_labelstudio_urls.py
```

**Verify the fixed JSON:**
```bash
python3 -c "import json; data = json.load(open('scripts/labelstudio-import-fixed.json')); print(f'Tasks: {len(data)}'); print(f'First URL: {data[0][\"data\"][\"image\"]}')"
```

---

## Troubleshooting

### Still getting "URL is valid" error?

Try using `localhost` instead of IP:
1. Edit `scripts/fix_labelstudio_urls.py`
2. Change `HOST_IP = "172.16.20.161"` to `HOST_IP = "localhost"`
3. Re-run: `python3 scripts/fix_labelstudio_urls.py`
4. Import the new fixed file

### Images still not loading?

1. Verify container is running: `docker ps | grep label-studio`
2. Check images exist: `docker exec label-studio ls /label-studio/data/media/upload/dataset-for-viz/ | wc -l` (should show 216)
3. Verify Label Studio can access them by opening a task and checking browser console for 404 errors

---

## Success Indicators

✅ **Import completes without errors**
✅ **Task count shows 195 in Label Studio**
✅ **First task displays image**
✅ **Green polygon overlays appear**
✅ **Polygons are editable**

---

**Ready to import!** Use `scripts/labelstudio-import-fixed.json` in Label Studio.

**File location:** `/home/mindmap/Desktop/dutch-parking-detection/scripts/labelstudio-import-fixed.json`

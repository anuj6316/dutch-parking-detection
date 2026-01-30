# Quick Start: Import Dataset into Label Studio

## 1. Access Label Studio
Open in browser: **http://localhost:8080**
- Username: `admin`
- Password: `admin`

## 2. Create Project
1. Click "Create Project"
2. Name: `Parking Dataset - 195 Tasks`
3. Click "Create"

## 3. Configure Labeling Interface
1. Go to Settings → Labeling Interface
2. Copy from: `scripts/labelstudio-config.xml`
3. Paste and click "Save"

**Configuration to paste:**
```xml
<View>
  <Image name="image" value="$image" zoom="true" zoomControl="true"/>
  <PolygonLabels name="label" toName="image" fillOpacity="0.2" strokeWidth="3">
    <Label value="Parking" background="green"/>
  </PolygonLabels>
</View>
```

## 4. Import Tasks
1. Click "Import" → "Upload from file"
2. Select: `scripts/labelstudio-import.json`
3. Click "Import Tasks"

## 5. Enable Predictions Display
1. Go to Settings → Machine Learning
2. Enable: "Show predictions to annotators in Label Stream and Quick View"
3. Click "Save"

## 6. Start Annotating
- Open first task from Label Stream
- Green polygons appear as pre-annotations
- Edit polygon points as needed
- Submit when complete

---

**Files Used:**
- Configuration: `scripts/labelstudio-config.xml`
- Import file: `scripts/labelstudio-import.json`
- Summary: `scripts/LABELSTUDIO_IMPORT_SUMMARY.md`

**Statistics:**
- Total tasks: 195
- Images: 1536×1536 PNG
- Average polygons per image: 4.4
- Label: Parking (green)

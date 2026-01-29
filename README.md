# dutch-parking-detection

## Step: 01 
`uv add -r requirements.txt`
`uv sync`

## Step: 02
`cd new_frontend`
`npm install -i`

## Step: 03
`uv run poe new_dev`: for running both frontend and backend at once
`uv run poe new_frontend`: only the frontend
`uv run poe backend`: only the backend

### Note
**Enable SAM3 model for car detection**: 
`/home/mindmap/Desktop/dutch-parking-detection/backend/vehicle_counter.py`: SKIP_SAM3_LOADING=False

**Model Path Setup**
`/home/mindmap/Desktop/dutch-parking-detection/backend/config.py`: 

Most general working model
`/home/mindmap/Desktop/dutch-parking-detection/yolo26s-obb-heavy-aug6/weights/best.pt`


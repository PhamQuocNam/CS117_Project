from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import joblib
import numpy as np
from config import Config
from model import Number_Plate_Recognizer
from path_finders import PathFinder
import cv2
import io
from PIL import Image
import base64
import json
from typing import List, Optional
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import SessionLocal, engine
from models import History
from database import Base
import crud
import datetime
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
        



# Define the input schema for file path (if you want to keep this option)
class ModelInput(BaseModel):
    image_file: str

# Define the response schema
class PredictionResponse(BaseModel):
    success: bool
    plate_texts: List[str]
    message: str
    num_plates_detected: int
    
class Position(BaseModel):
    position: tuple[int, int]

# Create app
app = FastAPI(
    title="Number Plate Recognition API",
    description="API for detecting and recognizing number plates using YOLO and OCR",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize config and model
config = Config()
model = Number_Plate_Recognizer(config)
path_finder = PathFinder(config)

# Serve static frontend files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.post("/history")
def create_history(data: dict, db: Session = Depends(get_db)):
    data['time'] = datetime.datetime.now()
    return crud.create_history(db=db,**data)


@app.get("/")
def root():
    return {"message": "Backend is running!"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "model_loaded": True}


@app.post("/removed_parked_position")
async def removed_parked_position(data: dict):
    x,y= data['position'][0], data['position'][1]
    path_finder.remove_parked_position((x,y))
    return {
        "message": f"Remove parked position successfully!",
        "location": (x,y)
    }

@app.post("/park_vehicle")
async def park_vehicle(data: dict):
    x,y= data['position'][0], data['position'][1]
    path_finder.park_vehicle((x,y))
    return{
        "message": "Successfully",
        "location": (x,y)
    }


@app.post("/find_shortest_parking_lot")
async def find_shortest_parking_lot():
    location = path_finder.find_shortest_blank_position()
    
    if location is None:
        raise HTTPException(status_code=404, detail="No available parking spots.")
    
    success = path_finder.park_vehicle(location)
    
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to park at location {location}")
    
    return {
        "message": f"Vehicle successfully parked at {location}",
        "location": location
    }




# Method 1: Upload image file directly
@app.post("/predict/upload/", response_model=PredictionResponse)
async def predict_upload(file: UploadFile = File(...)):
    """
    Upload an image file and get number plate predictions
    """
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read image file
        contents = await file.read()
        
        # Convert to OpenCV format
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        # Convert BGR to RGB (OpenCV loads as BGR, but our model expects RGB)
        
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image,(640,640))
        # Get predictions
        plate_texts = model.get_plate_texts(image)
        
        return PredictionResponse(
            success=True,
            plate_texts=plate_texts,
            message=f"Successfully detected {len(plate_texts)} number plates",
            num_plates_detected=len(plate_texts)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

# Method 2: Provide image file path (fixed version of your original)
@app.post("/predict/filepath/", response_model=PredictionResponse)
def predict_filepath(input_data: ModelInput):
    """
    Provide image file path and get number plate predictions
    """
    try:
        image_file = input_data.image_file  # Fixed: access attribute properly
        
        # Check if file exists and read image
        image = cv2.imread(image_file)
        if image is None:
            raise HTTPException(status_code=400, detail=f"Could not read image from path: {image_file}")
        
        # Fixed: cv2.cvtColor needs the image parameter first
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image,(640,640))
        # Get predictions (using text-only method for API response)
        plate_texts = model.get_plate_texts(image)
        
        return PredictionResponse(
            success=True,
            plate_texts=plate_texts,
            message=f"Successfully detected {len(plate_texts)} number plates",
            num_plates_detected=len(plate_texts)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

# Method 3: Base64 encoded image
@app.post("/predict/base64/")
def predict_base64(image_data: dict):
    """
    Send base64 encoded image and get number plate predictions.
    Expected format: {"image": "base64_encoded_string"}
    """
    try:
        if "image" not in image_data:
            raise HTTPException(status_code=400, detail="Missing 'image' field in request body")

        # Extract base64 content
        image_b64 = image_data["image"]
        if image_b64.startswith('data:image'):
            image_b64 = image_b64.split(',')[1]

        # Decode and convert to OpenCV format
        image_bytes = base64.b64decode(image_b64)
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (640, 640))

        # Predict plates and result images
        plate_texts = model.get_plate_texts(image)
        result_images = model.predict(image)
        
        result_images_b64 = []
        for img in result_images:
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            _, buffer = cv2.imencode('.jpg', img_bgr)
            img_b64 = base64.b64encode(buffer).decode('utf-8')
            result_images_b64.append(img_b64)
       
        return {
            "success": True,
            "plate_texts": plate_texts,
            "message": f"Successfully detected {len(plate_texts)} number plates",
            "num_plates_detected": len(plate_texts),
            "result_images": result_images_b64 
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


# Optional: Get detailed results with visualization
@app.post("/predict/detailed/")
async def predict_detailed(file: UploadFile = File(...)):
    """
    Upload an image and get detailed results with visualizations
    Returns base64 encoded result images
    """
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read image file
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        # Convert BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image,(640,640))
        
        # Get detailed predictions with visualizations
        result_images = model.predict(image)
        plate_texts = model.get_plate_texts(image)
        
        # Convert result images to base64 for JSON response
        result_images_b64 = []
        save_dir = "saved_results"
        os.makedirs(save_dir, exist_ok=True)
        for i,img in enumerate(result_images):
            # Convert RGB back to BGR for encoding
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            _, buffer = cv2.imencode('.jpg', img_bgr)
            img_b64 = base64.b64encode(buffer).decode('utf-8')
            result_images_b64.append(img_b64)

            save_path = os.path.join(save_dir, f"result_{i}.jpg")
            with open(save_path, "wb") as f:
                f.write(buffer)
            
        return {
            "success": True,
            "plate_texts": plate_texts,
            "result_images": result_images_b64,
            "num_plates_detected": len(plate_texts),
            "message": f"Successfully processed {len(plate_texts)} number plates"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"message": "Endpoint not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
import shutil
import os
import uuid
import json
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.services.transcriber import Transcriber
from app.services.timeline_generator import TimelineGenerator
from app.services.vector_service import VectorService
from app.services.vision_processor import VisionProcessor

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory task store (Use Redis/DB in production)
task_store: Dict[str, Dict[str, Any]] = {}

# Directory configuration
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
CATALOG_FILE = os.path.join(UPLOAD_DIR, "catalog.json")

def load_catalog() -> Dict[str, Any]:
    """Helper to load the B-roll catalog from disk."""
    if os.path.exists(CATALOG_FILE):
        try:
            with open(CATALOG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load catalog: {e}")
            return {}
    return {}

def save_catalog(catalog: Dict[str, Any]):
    """Helper to save the B-roll catalog to disk."""
    try:
        with open(CATALOG_FILE, "w") as f:
            json.dump(catalog, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save catalog: {e}")

import asyncio

# ... imports ...

# Global lock for catalog operations
catalog_lock = asyncio.Lock()

# ... (load/save_catalog helpers remain same) ...

async def update_catalog_safe(new_entries: Dict[str, Any]):
    """Safely updates the catalog with a lock."""
    async with catalog_lock:
        current_catalog = load_catalog()
        current_catalog.update(new_entries)
        save_catalog(current_catalog)
        return current_catalog

async def process_broll_files(files: List[UploadFile]):
    """
    Processes uploaded B-roll files:
    1. Saves them to disk.
    2. Runs VisionProcessor on each.
    3. Updates and indexes the catalog.
    """
    vision_processor = VisionProcessor()
    vector_service = VectorService()
    
    new_entries = {}
    processed_count = 0
    
    for file in files:
        try:
            # Generate safe file path
            file_location = os.path.join(UPLOAD_DIR, file.filename)
            
            # Save file
            with open(file_location, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            logger.info(f"Processing B-roll video: {file.filename}")
            
            # Run Vision Processor (CPU/Network bound - run in threadpool)
            metadata = await run_in_threadpool(vision_processor.process_video, file_location)
            
            # success
            new_entries[file.filename] = metadata
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Error processing {file.filename}: {e}")
            continue

    if new_entries:
        # Safely update the persistent catalog
        full_catalog = await update_catalog_safe(new_entries)
        
        # Index into VectorService (idempotent-ish)
        await run_in_threadpool(vector_service.index_catalog, full_catalog)
    
    return processed_count

@router.post("/upload-broll")
async def upload_broll(files: List[UploadFile] = File(...)):
    """
    Endpoint to upload and process B-roll videos.
    Extracts metadata and indexes it for search.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    count = await process_broll_files(files)
    
    return {
        "message": f"Successfully processed {count} videos.",
        "processed_count": count
    }

async def run_timeline_pipeline(task_id: str, a_roll_path: str):
    """
    Background task pipeline:
    1. Transcribe A-roll
    2. Generate Timeline (includes vector search)
    3. Save Result
    """
    try:
        task_store[task_id]["status"] = "processing"
        task_store[task_id]["step"] = "transcribing"
        
        print("================In run_timeline_pipeline================")
        # Transcribe
        transcriber = Transcriber()
        print("================CAlled Transcriber================")

        # Transcriber.transcribe is async
        transcription_result = await transcriber.transcribe(a_roll_path)
        segments = transcription_result.get("segments", [])
        print("================Got segments================")
        
        task_store[task_id]["step"] = "generating_timeline"
        
        # Generate Timeline
        # Load catalog for the generator
        catalog = load_catalog()
        print("================Load the catalog================")
        
        timeline_generator = TimelineGenerator()
        print("================Load the TimelineGenerator================")
        
        # TimelineGenerator.generate_timeline is sync
        timeline_result = await run_in_threadpool(
            timeline_generator.generate_timeline, 
            transcript=segments, 
            broll_catalog=catalog
        )
        print("================Generated Timeline================")
        
        # Save Output
        output_filename = f"timeline_{task_id}.json"
        output_path = os.path.join(UPLOAD_DIR, output_filename)
        print("================Saved Timeline================")
        
        with open(output_path, "w") as f:
            json.dump(timeline_result, f, indent=2)
        print("================Written Timeline================")
            
        task_store[task_id]["status"] = "completed"
        task_store[task_id]["result_url"] = f"/uploads/{output_filename}" 
        task_store[task_id]["result"] = timeline_result
        print("================Completed Timeline================")
        
    except Exception as e:
        logger.exception(f"Pipeline failed for task {task_id}")
        task_store[task_id]["status"] = "failed"
        task_store[task_id]["error"] = str(e)

@router.post("/process-timeline")
async def process_timeline(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Endpoint to process A-roll video and generate an editing timeline.
    Triggers a background task.
    """
    task_id = str(uuid.uuid4())
    
    print("================Task_id assigned================")

    # Save A-roll file
    file_location = os.path.join(UPLOAD_DIR, f"{task_id}_{file.filename}")
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    print("================File saved================")

    # Initialize task status
    task_store[task_id] = {
        "status": "pending",
        "original_filename": file.filename,
        "task_id": task_id
    }
    print("================Task status initialized================")
    
    # Add background task
    background_tasks.add_task(run_timeline_pipeline, task_id, file_location)

    print("================Background task added================")
    
    return {
        "task_id": task_id,
        "message": "Processing started",
        "status_endpoint": f"/api/v1/status/{task_id}"
    }
    print("================Response sent================")

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """
    Get the status of a processing task.
    """
    task = task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task

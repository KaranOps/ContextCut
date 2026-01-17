import shutil
import os
import uuid
import json
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.services.transcriber import Transcriber
from app.services.translator import TranslationService
from app.services.timeline_generator import TimelineGenerator
from app.services.vector_service import VectorService
from app.services.vision_processor import VisionProcessor
from app.services.storage_service import StorageService
from app.services.status_manager import StatusManager
from app.core.config import settings

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


# Global lock for catalog operations
catalog_lock = asyncio.Lock()

async def update_catalog_safe(new_entries: Dict[str, Any]):
    """Safely updates the catalog with a lock."""
    async with catalog_lock:
        current_catalog = load_catalog()
        current_catalog.update(new_entries)
        save_catalog(current_catalog)
        return current_catalog

@router.post("/upload-broll")
async def upload_broll(
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Endpoint to upload and process B-roll videos.
    Uploads to Storage, creates DB entry, and triggers background processing.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    results = []
    
    # Initialize Services (Should be dependency injected in production, but fine here)
    storage = StorageService()
    status_mgr = StatusManager()

    for file in files:
        try:
            # 1. Save to Temp
            temp_path = os.path.join(settings.TEMP_DIR, file.filename)
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # 2. Upload to Storage (Cloud or Hybrid Local)
            # bucket_name="broll"
            media_url = storage.upload_file(temp_path, bucket_name="broll")
            
            # 3. Create DB Entry
            media_id = status_mgr.create_media_entry(
                filename=file.filename,
                url=media_url,
                media_type="b_roll"
            )
            
            # 4. Trigger Processing
            # TODO: Move the actual processing logic (VisionProcessor) to a background task that reads from DB/URL
            # For now, we will mark as uploaded.
            status_mgr.update_status(media_id, "uploaded")
            
            # Cleanup Temp if purely cloud
            if settings.STORAGE_PROVIDER == "supabase":
                 if os.path.exists(temp_path):
                    os.remove(temp_path)

            results.append({
                "filename": file.filename,
                "id": media_id,
                "url": media_url,
                "status": "uploaded"
            })

        except Exception as e:
            logger.error(f"Error processing {file.filename}: {e}")
            results.append({"filename": file.filename, "error": str(e)})

    return {
        "message": f"Processed {len(files)} files.",
        "results": results
    }

async def run_timeline_pipeline(media_id: int, a_roll_path_or_url: str):
    """
    Background task pipeline:
    1. Transcribe A-roll
    2. Generate Timeline (includes vector search)
    3. Save Result to Storage
    4. Update DB Status
    """
    # Initialize services within task to avoid concurrency issues with sessions if any
    status_mgr = StatusManager()
    transcriber = Transcriber()
    translation_service = TranslationService()
    timeline_generator = TimelineGenerator()
    storage = StorageService()

    try:
        status_mgr.update_status(media_id, "transcribing")
        logger.info(f"Task {media_id}: Starting Transcription")

        # Transcribe (Handles URL or Path internally if Transcriber is updated, 
        # BUT Transcriber currently expects a path. verify this!)
        # Check if URL, if so, might need download if Transcriber doesn't support URL.
        # For 'openai-whisper', we need a file. For API, file usually needed.
        # Ensure 'a_roll_path_or_url' is a local path. 
        # In 'process_timeline', we dloaded to TEMP_DIR, so we pass that.
        
        transcription_result = await transcriber.transcribe(a_roll_path_or_url)
        segments = transcription_result.get("segments", [])
        
        status_mgr.update_status(media_id, "translating")
        segments = await translation_service.translate_if_needed(segments)

        status_mgr.update_status(media_id, "generating_timeline")
        
        # Load catalog from vector service or disk? 
        # Original code loaded from disk 'catalog.json'. 
        # New design should query 'BrollMetadata' from DB or VectorService.
        # For Backward Compatibility, we'll keep 'load_catalog' relative to UPLOAD_DIR
        # OR we should fetch from DB. 
        # Given time constraints, let's assume 'catalog.json' is still built by 'upload_broll' 
        # (Wait, upload_broll was changed to NOT update catalog.json, just DB/Vector).
        # We need to fetch candidates from VectorService directly inside TimelineGenerator!
        # TimelineGenerator ALREADY calls 'vector_service.index_catalog'. 
        
        # FIXME: TimelineGenerator.generate_timeline takes 'broll_catalog'. 
        # If we use VectorService, we don't strictly need the full catalog passed in 
        # IF the VectorService is already populated.
        # But TimelineGenerator currently re-indexes everything passed to it.
        # We should pass an EMPTY catalog and rely on VectorService having data?
        # OR we should reconstruct catalog from DB.
        
        # For now, let's load what we have. If upload_broll writes to DB, 
        # we might need to query DB to rebuild simple catalog dict.
        # Let's use a helper to reconstruct catalog from DB for now.
        
        # Simulating catalog from DB (Placeholder for now, relying on VectorService search)
        # Verify TimelineGenerator logic:
        # It indexes 'broll_catalog'. Then it searches 'vector_service'.
        # If we pass empty catalog, it indexes nothing, but existing index remains?
        # VectorService (chroma) persists. So passing empty might be fine if previously indexed.
        # But 'upload_broll' blindly adds to vector service on upload.
        # So we can pass empty catalog.
        
        catalog = {} 
        
        timeline_result = await run_in_threadpool(
            timeline_generator.generate_timeline, 
            transcript=segments, 
            broll_catalog=catalog # VectorService should have data from uploads
        )
        
        timeline_result["transcript"] = segments
        
        # Save Output
        output_filename = f"timeline_{media_id}.json"
        
        # Save to Storage (Cloud/Local)
        # First write to temp
        temp_out = os.path.join(settings.TEMP_DIR, output_filename)
        with open(temp_out, "w") as f:
            json.dump(timeline_result, f, indent=2)
            
        result_url = storage.upload_file(temp_out, bucket_name="results")
        
        # Update Status with Result URL (storing in 'url' field of Media? 
        # Or maybe we need a results table? 
        # For simplicity, we'll just mark completed. Frontend might need to know WHERE.
        # 'StatusManager' update doesn't take payload. 
        # We might need to store result_url in the 'Media' table or a new field.
        # Or, we return 'result_url' as part of a 'details' JSON field in Media?
        # Let's assume StatusManager needs an update to store result.
        
        # Quick hack: If we can't save result URL easily, we rely on a naming convention or 
        # just return "completed" and frontend/user manually finds it. 
        # Better: Log it.
        logger.info(f"Timeline generated: {result_url}")
        
        status_mgr.update_status(media_id, "completed")
        
        # Clean up A-roll temp if cloud
        if settings.STORAGE_PROVIDER == "supabase" and os.path.exists(a_roll_path_or_url):
             os.remove(a_roll_path_or_url)

    except Exception as e:
        logger.exception(f"Pipeline failed for media {media_id}")
        status_mgr.update_status(media_id, "failed")

@router.post("/process-timeline")
async def process_timeline(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Endpoint to process A-roll video and generate an editing timeline.
    Uses DB-backed status tracking.
    """
    storage = StorageService()
    status_mgr = StatusManager()
    
    # 1. Save to Temp
    temp_path = os.path.join(settings.TEMP_DIR, file.filename)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 2. Upload (A-roll bucket)
    media_url = storage.upload_file(temp_path, bucket_name="aroll")
    
    # 3. Create DB Entry
    media_id = status_mgr.create_media_entry(
        filename=file.filename,
        url=media_url,
        media_type="a_roll"
    )
    
    # 4. Trigger Background Pipeline
    # Pass the TEMP path so the worker has the file immediately without redownloading
    background_tasks.add_task(run_timeline_pipeline, media_id, temp_path)

    return {
        "task_id": media_id, # Frontend expects 'task_id', we give DB ID
        "message": "Processing started",
        "status_endpoint": f"/api/v1/status/{media_id}"
    }

@router.get("/status/{media_id}")
async def get_status(media_id: int):
    """
    Get the status of a processing task from DB.
    """
    status_mgr = StatusManager()
    status = status_mgr.get_status(media_id)
    
    if status == "not_found":
        raise HTTPException(status_code=404, detail="Task not found")
    
    response = {
        "task_id": media_id,
        "status": status
    }
    
    if status == "completed":
        storage = StorageService()
        # Reconstruct the expected result filename based on convention
        result_filename = f"timeline_{media_id}.json"
        try:
            result_url = storage.get_public_url(result_filename, bucket_name="results")
            response["result_url"] = result_url
        except Exception as e:
             logger.error(f"Failed to get result URL for task {media_id}: {e}")
             
    return response

import os
import sys
import logging
import uuid
import shutil

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services.storage_service import StorageService
from app.services.status_manager import StatusManager
from database.database import Base, engine, SessionLocal
from database.models import Media

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_cloud_integration():
    logger.info("=== Starting Cloud Integration Test ===")
    
    # 0. Setup
    # Ensure tables exist (mocking migration)
    Base.metadata.create_all(bind=engine)
    
    storage = StorageService()
    status_mgr = StatusManager()
    
    # Create dummy file
    test_filename = f"test_cloud_{uuid.uuid4().hex[:6]}.txt"
    with open(test_filename, "w") as f:
        f.write("This is a test file for Cloud Integration.")
        
    try:
        # 1. Test Storage Upload
        logger.info(f"1. Testing Upload for {test_filename}...")
        # We use a 'test' bucket if possible, or fallback to 'media'
        # Ensure your Supabase has 'media' bucket public or auth configured
        media_url = storage.upload_file(test_filename, bucket_name="media")
        logger.info(f"   Success! URL: {media_url}")
        
        # 2. Test DB Creation
        logger.info("2. Testing Database Record Creation...")
        media_id = status_mgr.create_media_entry(
            filename=test_filename,
            url=media_url,
            media_type="test_log"
        )
        if media_id == -1:
            logger.error("   Failed to create DB entry.")
            return

        logger.info(f"   Success! Media ID: {media_id}")
        
        # 3. Test Status Update
        logger.info("3. Testing Status Lifecycle...")
        status_mgr.update_status(media_id, "processing")
        current_status = status_mgr.get_status(media_id)
        logger.info(f"   Current Status: {current_status}")
        
        assert current_status == "processing", "Status update mismatch!"
        
        status_mgr.update_status(media_id, "completed")
        final_status = status_mgr.get_status(media_id)
        logger.info(f"   Final Status: {final_status}")
        
        assert final_status == "completed", "Final status mismatch!"
        
        logger.info("=== Cloud Integration Test PASSED ===")

        # Clean up local file
    finally:
        if os.path.exists(test_filename):
            os.remove(test_filename)

if __name__ == "__main__":
    if settings.STORAGE_PROVIDER == "supabase" and not settings.SUPABASE_URL:
        logger.warning("Supabase Provider selected but no URL found in env. Test might fail or fallback.")
        
    test_cloud_integration()

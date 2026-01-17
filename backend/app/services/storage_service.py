import os
import shutil
import logging
from typing import Optional
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.provider = settings.STORAGE_PROVIDER
        self.supabase: Optional[Client] = None
        self.temp_dir = settings.TEMP_DIR
        
        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)

        if self.provider == "supabase":
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                logger.error("Supabase credentials missing. Falling back to local storage.")
                self.provider = "local"
            else:
                try:
                    self.supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                except Exception as e:
                    logger.error(f"Failed to initialize Supabase client: {e}")
                    self.provider = "local"

    def upload_file(self, file_path: str, bucket_name: str = "media", destination_path: str = None) -> str:
        """
        Uploads a file to the configured storage provider.
        Returns a URL (or local path) to access the file.
        """
        filename = os.path.basename(file_path)
        dest_path = destination_path or filename

        if self.provider == "supabase":
            try:
                # Read file content
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                # Upload to Supabase Storage
                # Note: 'upsert' option might be needed depending on policy
                response = self.supabase.storage.from_(bucket_name).upload(
                    path=dest_path,
                    file=file_content,
                    file_options={"upsert": "true"}
                )
                
                # Get Public URL
                public_url = self.supabase.storage.from_(bucket_name).get_public_url(dest_path)
                logger.info(f"Uploaded to Supabase: {public_url}")
                return public_url
                
            except Exception as e:
                logger.error(f"Supabase upload failed: {e}. Falling back to local copy.")
                # Fallthrough to local behavior on failure? Or raise?
                # For robust hybrid, let's fallthrough or raise. 
                # Ideally raise, but for user testing fallback is nice.
                # Let's raise to ensure they know cloud failed.
                raise e

        else: # Local Provider
            # Mimic "upload" by copying to a persistent uploads dir if needed, 
            # or just returning the path if it's already in a mostly permanent place.
            # Assuming 'uploads' dir in root as the "bucket" analogue.
            
            # For simplicity in local mode, we might just return the absolute path 
            # if the file is already on disk.
            # BUT, if we want to simulate an upload to a specific "bucket" folder:
            
            target_dir = os.path.join(settings.DATA_DIR, "uploads", bucket_name)
            os.makedirs(target_dir, exist_ok=True)
            
            final_path = os.path.join(target_dir, dest_path)
            if os.path.abspath(file_path) != os.path.abspath(final_path):
                shutil.copy2(file_path, final_path)
                
            logger.info(f"Stored locally: {final_path}")
            return str(final_path)

    def get_public_url(self, path: str, bucket_name: str = "media") -> str:
        if self.provider == "supabase":
            return self.supabase.storage.from_(bucket_name).get_public_url(path)
        else:
            # Return absolute path for local files
            return os.path.join(settings.DATA_DIR, "uploads", bucket_name, path)

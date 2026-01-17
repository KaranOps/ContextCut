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

    def _save_local(self, file_path: str, bucket_name: str, dest_path: str) -> str:
        """Helper to save file locally."""
        target_dir = os.path.join(settings.DATA_DIR, "uploads", bucket_name)
        os.makedirs(target_dir, exist_ok=True)
        
        final_path = os.path.join(target_dir, dest_path)
        # Ensure distinct paths before copying
        if os.path.abspath(file_path) != os.path.abspath(final_path):
            shutil.copy2(file_path, final_path)
            
        logger.info(f"Stored locally: {final_path}")
        return str(final_path)

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
                # Helper to check for bucket not found error
                # Supabase/Postgrest errors vary, often standard HTTP exceptions or dicts
                error_str = str(e).lower()
                if "bucket not found" in error_str:
                    logger.warning(f"Bucket '{bucket_name}' not found. Attempting to create it...")
                    try:
                        self.supabase.storage.create_bucket(bucket_name, options={"public": True})
                        
                        # Resize/read file again if needed (cursor might be at end if read previously?)
                        # We read into 'file_content' variable, so we can reuse it.
                        
                        self.supabase.storage.from_(bucket_name).upload(
                            path=dest_path,
                            file=file_content,
                            file_options={"upsert": "true"}
                        )
                        public_url = self.supabase.storage.from_(bucket_name).get_public_url(dest_path)
                        logger.info(f"Uploaded to Supabase after creation: {public_url}")
                        return public_url
                    except Exception as create_err:
                        logger.error(f"Failed to create bucket or retry upload: {create_err}")
                else:
                    logger.error(f"Supabase upload failed: {e}.")
                    raise e

        else: # Local Provider
            return self._save_local(file_path, bucket_name, dest_path)

    def get_public_url(self, path: str, bucket_name: str = "media") -> str:
        if self.provider == "supabase":
            return self.supabase.storage.from_(bucket_name).get_public_url(path)
        else:
            # Return absolute path for local files
            return os.path.join(settings.DATA_DIR, "uploads", bucket_name, path)

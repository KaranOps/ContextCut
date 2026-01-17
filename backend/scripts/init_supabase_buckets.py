import sys
import os
from pathlib import Path

# Add backend directory to path so we can import app modules
backend_path = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_path))

from app.core.config import settings
from supabase import create_client

def init_buckets():
    print(f"Connecting to Supabase: {settings.SUPABASE_URL}")
    if not settings.SUPABASE_KEY:
        print("Error: SUPABASE_KEY is missing!")
        return

    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    buckets_to_create = ["broll", "aroll", "results"]
    
    existing_buckets = []
    try:
        res = supabase.storage.list_buckets()
        existing_buckets = [b.name for b in res]
        print(f"Existing buckets: {existing_buckets}")
    except Exception as e:
        print(f"Failed to list buckets: {e}")
        # Proceeding to try creating anyway might fail if listing failed, but worth a try or exit?
        # If we can't list, we probably can't create. 
        # But let's try creating one to see the specific error.

    for bucket in buckets_to_create:
        if bucket not in existing_buckets:
            print(f"Creating bucket: {bucket}...")
            try:
                supabase.storage.create_bucket(bucket, options={"public": True})
                print(f"Successfully created bucket: {bucket}")
            except Exception as e:
                print(f"Failed to create bucket '{bucket}': {e}")
        else:
            print(f"Bucket '{bucket}' already exists.")

if __name__ == "__main__":
    init_buckets()

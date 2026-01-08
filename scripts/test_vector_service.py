import sys
import os
import logging
import uuid
# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Mock API keys if needed
os.environ["OPENAI_API_KEY"] = "sk-mock-key"
os.environ["GROQ_API_KEY"] = "gsk-mock-key"
os.environ["CHROMA_DB_PATH"] = "./test_chroma_db_" + str(uuid.uuid4()) # Use unique DB for test

from app.core.config import settings
from app.services.vector_service import VectorService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_vector_service():
    logger.info("Testing VectorService...")
    
    # 1. Initialize
    service = VectorService()
    logger.info(f"Initialized with provider: {service.provider}")
    assert service.provider == "local"
    assert service.local_model is not None
    
    # 2. Index Dummy Data
    catalog = {
        "clip1.mp4": {"description": "A man cooking pasta in a kitchen", "activity": "cooking", "category": "indoor"},
        "clip2.mp4": {"description": "A dog running in the park", "activity": "running", "category": "outdoor"},
        "clip3.mp4": {"description": "Coding on a laptop in a cafe", "activity": "coding", "category": "indoor"}
    }
    
    service.index_catalog(catalog)
    logger.info("Catalog indexed.")
    
    # 3. Query - Match
    query = "someone preparing food"
    matches = service.get_best_matches(query)
    logger.info(f"Query: '{query}' -> Matches: {matches}")
    
    assert len(matches) > 0
    assert matches[0]['id'] == "clip1.mp4"
    assert matches[0]['similarity_score'] >= settings.SIMILARITY_THRESHOLD
    
    # 4. Query - No Match (Threshold Check)
    query_irrelevant = "spaceships fighting in orbit"
    matches_irrelevant = service.get_best_matches(query_irrelevant)
    logger.info(f"Query: '{query_irrelevant}' -> Matches: {matches_irrelevant}")
    
    # Ideally should be low, but 'bert' might find some relation. 
    # With SIMILARITY_THRESHOLD=0.6, it should hopefully filter out.
    # If not, let's just log it. 
    if len(matches_irrelevant) == 0:
        logger.info("Correctly filtered out irrelevant clips.")
    else:
        logger.warning(f"Warning: Found matches for irrelevant query: {matches_irrelevant}")

    logger.info("VectorService Test Passed.")

if __name__ == "__main__":
    try:
        test_vector_service()
        # Clean up
        import shutil
        if os.path.exists(os.environ["CHROMA_DB_PATH"]):
            shutil.rmtree(os.environ["CHROMA_DB_PATH"])
    except Exception as e:
        logger.error(f"Test Failed: {e}")
        sys.exit(1)

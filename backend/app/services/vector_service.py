import logging
import os
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from app.core.config import settings

logger = logging.getLogger(__name__)

class VectorService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            logger.info("VectorService already initialized. Skipping re-initialization.")
            return
            
        logger.info(f"Initializing VectorService with provider: {settings.EMBEDDING_PROVIDER}")
        
        # Initialize ChromaDB
        os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
        # Using persistent client
        self.chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        
        # Initialize Model
        self.provider = settings.EMBEDDING_PROVIDER
        self.local_model = None
        self.openai_client = None

        if self.provider == "local":
            logger.info(f"Loading local model: {settings.LOCAL_MODEL_NAME}")
            try:
                self.local_model = SentenceTransformer(settings.LOCAL_MODEL_NAME, trust_remote_code=True)
            except Exception as e:
                logger.error(f"Failed to load local model {settings.LOCAL_MODEL_NAME}: {e}")
                # Fallback or re-raise? Re-raising as this is critical.
                raise
        elif self.provider == "openai":
            from openai import OpenAI
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        self._initialized = True

    def _get_collection_name(self) -> str:
        """
        Generates a collection name based on the current model.
        """
        if self.provider == "local":
            safe_name = settings.LOCAL_MODEL_NAME.replace("/", "_").replace("-", "_").replace(".", "_")
            return f"{settings.COLLECTION_NAME_PREFIX}_{safe_name}"
        else:
            return f"{settings.COLLECTION_NAME_PREFIX}_openai"

    def _get_embedding(self, text: str) -> List[float]:
        if self.provider == "local":
            return self.local_model.encode(text).tolist()
        elif self.provider == "openai":
            response = self.openai_client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
        return []

    def index_catalog(self, broll_catalog: Dict[str, Any]):
        """
        Indexes the B-roll catalog into ChromaDB.
        """
        collection_name = self._get_collection_name()
        logger.info(f"Indexing catalog into collection: {collection_name}")
        
        # Ensure collection exists with cosine similarity
        collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"} # Use cosine similarity
        )
        
        # Naive idempotency check: if count matches catalog size, skip.
        # Ideally we'd check hashes or IDs.
        if collection.count() >= len(broll_catalog):
            logger.info(f"Collection {collection_name} seems populated ({collection.count()} items). Skipping full re-index.")
            return

        ids = []
        documents = []
        metadatas = []
        embeddings = []

        logger.info(f"Generating embeddings for {len(broll_catalog)} items...")
        
        for filename, info in broll_catalog.items():
            # Handle list structure (multiple segments per file)
            segments = info if isinstance(info, list) else [info]
            
            # Aggregate descriptions from all segments
            # We'll validly assume the file represents a coherent concept, 
            # so fusing keywords is acceptable for retrieval.
            
            aggregated_parts = []
            first_valid_meta = {}
            
            for seg in segments:
                # Capture metadata from first valid segment for storage
                if not first_valid_meta and isinstance(seg, dict):
                    first_valid_meta = seg
                
                if isinstance(seg, dict):
                    parts = [
                        seg.get('description', ''),
                        seg.get('activity', ''),
                        seg.get('category', ''),
                        seg.get('visual_tag', ''),
                        seg.get('mood', '')
                    ]
                    # Flatten nested description dict if it exists 
                    desc_field = seg.get('description')
                    if isinstance(desc_field, dict):
                        parts.extend([
                            desc_field.get('activity', ''),
                            desc_field.get('category', ''),
                            desc_field.get('intent', '')
                        ])
                        
                    aggregated_parts.extend([str(p) for p in parts if p])
            
            description = " ".join(set(aggregated_parts)).strip() # Use set to dedup
            
            if not description:
                description = filename # Fallback
            
            ids.append(filename)
            documents.append(description)
            
            # Flatten metadata values to str/int/float for Chroma compatibility
            # We can't store nested dicts/lists in Chroma metadata directly
            flat_meta = {}
            if first_valid_meta:
                for k, v in first_valid_meta.items():
                    if isinstance(v, (str, int, float, bool)):
                        flat_meta[k] = v
                    elif isinstance(v, dict):
                        # Flatten one level of dict
                        for sub_k, sub_v in v.items():
                             if isinstance(sub_v, (str, int, float, bool)):
                                flat_meta[f"{k}_{sub_k}"] = sub_v
            
            metadatas.append(flat_meta) 
            embeddings.append(self._get_embedding(description))

        if ids:
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            logger.info("Indexing complete.")

    def get_best_matches(self, query_text: str) -> List[Dict[str, Any]]:
        """
        Retrieves top-K B-roll candidates for the given query.
        Filters by SIMILARITY_THRESHOLD.
        """
        collection_name = self._get_collection_name()
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
        except Exception:
            # Collection might not exist if index_catalog wasn't called
            logger.warning(f"Collection {collection_name} not found.")
            return []

        query_embedding = self._get_embedding(query_text)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=settings.VECTOR_TOP_K
        )

        candidates = []
        if results['ids']:
            ids = results['ids'][0]
            distances = results['distances'][0] # For 'cosine', distance = 1 - similarity
            metadatas = results['metadatas'][0]

            for i, dist in enumerate(distances):
                similarity = 1 - dist # Convert cosine distance to similarity
                if similarity >= settings.SIMILARITY_THRESHOLD:
                    item = metadatas[i]
                    item['id'] = ids[i]
                    item['similarity_score'] = similarity
                    candidates.append(item)
                else:
                    # Since results are sorted by distance (similarity desc), 
                    # we might stop early, but checking all top-K is safer.
                    pass
        
        return candidates

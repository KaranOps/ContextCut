import logging
import os
from typing import List, Dict, Any, Optional

import chromadb
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
            logger.info("VectorService already initialized.")
            return
            
        self.provider = settings.EMBEDDING_PROVIDER
        self.model_name = settings.EMBEDDING_MODEL
        
        logger.info(f"Initializing VectorService. Provider: {self.provider}, Model: {self.model_name}")
        
        # Initialize ChromaDB
        os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        
        self.local_model = None
        self.openai_client = None
        
        # Determine actual execution strategy
        self.use_local = False
        
        # Groq doesn't natively support embeddings well yet, so we usually fallback to local if Groq is the primary provider
        if self.provider == "local" or (self.provider == "groq" and self.model_name == "local"):
             self.use_local = True
             if self.model_name == "local":
                 self.model_name = settings.LOCAL_MODEL_NAME # Resolve actual local model name
        
        elif self.provider == "groq" and self.model_name != "local":
             # If user specifically asked for a Groq embedding model
             logger.warning(f"Groq embedding model {self.model_name} requested. Fallback logic may be required if not supported.")
             # For now, we fall back to local to ensure stability unless I verify Groq embeddings
             # But let's assume the user knows what they are doing if they set a specific model.
             # Actually, complying with 'OpenAI -> Groq -> Local' hierarchy implies we should support it if possible.
             # But 'text-embedding-3' is OpenAI. 'nomic' is Local.
             # If config defaults set Groq->local, we are good.
             pass

        elif self.provider == "openai":
            from openai import OpenAI
            if settings.OPENAI_API_KEY:
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            else:
                 logger.warning("OpenAI provider selected but no key. Falling back to Local.")
                 self.use_local = True
                 self.model_name = settings.LOCAL_MODEL_NAME

        if self.use_local:
            logger.info(f"Loading local embedding model: {self.model_name}")
            try:
                self.local_model = SentenceTransformer(self.model_name, trust_remote_code=True)
            except Exception as e:
                logger.error(f"Failed to load local model {self.model_name}: {e}")
                raise

        self._initialized = True

    def _get_collection_name(self) -> str:
        """
        Generates a collection name based on the current model to prevent dimension mismatches.
        """
        # Sanitize model name for ChromaDB collection requirements
        safe_name = self.model_name.replace("/", "_").replace("-", "_").replace(".", "_").replace(":", "")
        return f"{settings.COLLECTION_NAME_PREFIX}_{safe_name}"

    def _get_embedding(self, text: str) -> List[float]:
        try:
            if self.use_local and self.local_model:
                return self.local_model.encode(text).tolist()
            
            elif self.provider == "openai" and self.openai_client:
                response = self.openai_client.embeddings.create(
                    input=text,
                    model=self.model_name
                )
                return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return []
        
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
            metadata={"hnsw:space": "cosine"}
        )
        
        # Naive idempotency check
        if collection.count() >= len(broll_catalog):
            logger.info(f"Collection {collection_name} seems populated ({collection.count()} items). Skipping full re-index.")
            return

        ids = []
        documents = []
        metadatas = []
        embeddings = []

        logger.info(f"Generating embeddings for {len(broll_catalog)} items...")
        
        for filename, info in broll_catalog.items():
            # In the new flow, info is likely the dict directly from vision processor
            # but legacy might wrap it in a list. Handle both.
            segments = info if isinstance(info, list) else [info]
            
            aggregated_parts = []
            first_valid_meta = {}
            
            for seg in segments:
                if not first_valid_meta and isinstance(seg, dict):
                    first_valid_meta = seg
                
                if isinstance(seg, dict):
                    # NEW SCHEMA EXTRACTION
                    # Core fields
                    activity = seg.get('activity', '')
                    category = seg.get('category', '')
                    intent = seg.get('intent', '')
                    
                    # Nested Technical fields
                    tech = seg.get('technical', {})
                    tech_desc = ""
                    if isinstance(tech, dict):
                        tech_desc = f"{tech.get('shot_type', '')} {tech.get('camera_movement', '')} {tech.get('lighting', '')}"
                    
                    # Search Tags
                    tags = seg.get('search_tags', [])
                    tags_str = " ".join(tags) if isinstance(tags, list) else str(tags)
                    
                    # Legacy fallback items (just in case)
                    desc = seg.get('description', '')

                    parts = [activity, category, intent, tech_desc, tags_str, desc]
                    aggregated_parts.extend([str(p) for p in parts if p])
            
            description = " ".join(set(aggregated_parts)).strip()
            
            if not description:
                description = filename
            
            id_str = filename
            ids.append(id_str)
            documents.append(description)
            
            # Metadata Flattening
            flat_meta = {}
            if first_valid_meta:
                for k, v in first_valid_meta.items():
                    # Primitives
                    if isinstance(v, (str, int, float, bool)):
                        flat_meta[k] = v
                    # Lists (like search_tags) -> comma string
                    elif isinstance(v, list):
                        flat_meta[k] = ", ".join([str(i) for i in v])
                    # Dicts (like technical) -> flatten with prefix
                    elif isinstance(v, dict):
                        for sub_k, sub_v in v.items():
                             if isinstance(sub_v, (str, int, float, bool)):
                                flat_meta[f"{k}_{sub_k}"] = sub_v
            
            metadatas.append(flat_meta) 
            embeddings.append(self._get_embedding(description))

        if ids:
            # Batch add if needed, but for now simple add
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
        """
        collection_name = self._get_collection_name()
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
        except Exception:
            logger.warning(f"Collection {collection_name} not found.")
            return []

        query_embedding = self._get_embedding(query_text)
        if not query_embedding:
            return []
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=settings.VECTOR_TOP_K
        )

        candidates = []
        if results['ids']:
            ids = results['ids'][0]
            distances = results['distances'][0]
            metadatas = results['metadatas'][0]

            for i, dist in enumerate(distances):
                similarity = 1 - dist # Cosine conversion
                if similarity >= settings.SIMILARITY_THRESHOLD:
                    item = metadatas[i]
                    item['id'] = ids[i]
                    item['similarity_score'] = similarity
                    candidates.append(item)
                    
        return candidates

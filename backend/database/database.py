from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Hybrid DB Support: If no DB_URL, we can default to SQLite for local testing
# but implementation plan said Postgres. We'll stick to Postgres logic 
# but allow fallback if empty?
# For now, implemented as requested for Supabase/Postgres.

SQLALCHEMY_DATABASE_URL = settings.SUPABASE_DB_URL

# If not set, maybe fallback to a local sqlite?
if not SQLALCHEMY_DATABASE_URL:
    # Use a generic local sqlite for development if no cloud DB provided
    import os
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(settings.DATA_DIR, 'contextcut.db')}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

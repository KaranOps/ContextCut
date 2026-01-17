from sqlalchemy.orm import Session
from database.database import SessionLocal, engine
from database.models import Base, Media
import logging

logger = logging.getLogger(__name__)

# Ensure tables exist (for local sqlite fallback or initial run)
# Ideally managed by alembic, but for this scope auto-create is fine
Base.metadata.create_all(bind=engine)

class StatusManager:
    """
    Manages status updates for media processing.
    Writes to Database (Postgres/SQLite) to persist state.
    """
    def __init__(self):
        pass

    def get_db(self):
        return SessionLocal()

    def create_media_entry(self, filename: str, url: str, media_type: str) -> int:
        db = self.get_db()
        try:
            # Check if exists? For now just create new
            new_media = Media(
                filename=filename,
                url=url,
                type=media_type,
                status="pending"
            )
            db.add(new_media)
            db.commit()
            db.refresh(new_media)
            return new_media.id
        except Exception as e:
            logger.error(f"Failed to create media entry: {e}")
            db.rollback()
            return -1
        finally:
            db.close()

    def update_status(self, media_id: int, status: str):
        db = self.get_db()
        try:
            media = db.query(Media).filter(Media.id == media_id).first()
            if media:
                media.status = status
                db.commit()
                logger.info(f"Updated Status [ID: {media_id}] -> {status}")
            else:
                logger.warning(f"Media ID {media_id} not found for status update.")
        except Exception as e:
            logger.error(f"Failed to update status: {e}")
        finally:
            db.close()

    def get_status(self, media_id: int) -> str:
        db = self.get_db()
        try:
            media = db.query(Media).filter(Media.id == media_id).first()
            if media:
                return media.status
            return "not_found"
        finally:
            db.close()

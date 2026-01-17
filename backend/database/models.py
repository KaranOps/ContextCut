from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.database import Base

class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    url = Column(String) # Cloud URL or Local Path
    type = Column(String) # 'a_roll' or 'b_roll'
    status = Column(String, default="pending") # pending, processing, ready, error
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    metadata_entry = relationship("BrollMetadata", back_populates="media", uselist=False)

class BrollMetadata(Base):
    __tablename__ = "broll_metadata"

    id = Column(Integer, primary_key=True, index=True)
    media_id = Column(Integer, ForeignKey("media.id"))
    
    activity = Column(String)
    category = Column(String)
    intent = Column(String)
    tags = Column(String) # Comma-separated or JSON? Using String for simplicity/compatibility
    technical = Column(JSON) # Stores nested dict {shot_type, etc.}
    
    media = relationship("Media", back_populates="metadata_entry")

from pydantic import BaseModel
from typing import List, Optional

class TimelineEvent(BaseModel):
    start_time: float
    end_time: float
    description: str
    clip_type: str  # 'a-roll' or 'b-roll'

class Timeline(BaseModel):
    events: List[TimelineEvent]

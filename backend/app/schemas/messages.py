from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class MessageSend(BaseModel):
    room_id: str
    body: str
    msg_type: str = "m.text"


class MessageOut(BaseModel):
    event_id: str
    room_id: str
    sender: str
    sender_display_name: Optional[str] = None
    body: str
    msg_type: str = "m.text"
    timestamp: datetime
    file_url: Optional[str] = None
    filename: Optional[str] = None
    file_size: Optional[int] = None


class MessageHistory(BaseModel):
    messages: List[MessageOut]
    end_token: Optional[str] = None
    has_more: bool = False

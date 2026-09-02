from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class TeamMemberOut(BaseModel):
    hub_user_id: str
    display_name: Optional[str] = None


class TeamCreate(BaseModel):
    name: str
    member_hub_user_ids: List[str] = []


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    member_hub_user_ids: Optional[List[str]] = None


class TeamOut(BaseModel):
    id: int
    name: str
    members: List[TeamMemberOut] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TeamInviteResult(BaseModel):
    invited: List[str] = []
    already_member: List[str] = []
    failed: List[str] = []

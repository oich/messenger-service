from typing import Optional

from pydantic import BaseModel


class UserOut(BaseModel):
    hub_user_id: str
    matrix_user_id: str
    display_name: Optional[str] = None
    tenant_id: Optional[int] = None
    is_bot: bool = False

    class Config:
        from_attributes = True


class TokenData(BaseModel):
    username: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    matrix_user_id: str
    display_name: Optional[str] = None

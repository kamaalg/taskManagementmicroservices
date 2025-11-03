from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: str

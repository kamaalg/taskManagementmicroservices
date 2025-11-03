from typing import Optional, Literal
from pydantic import BaseModel

class TaskCreate(BaseModel):
    userId: str
    title: str
    description: Optional[str] = None
    status: Literal["pending", "in-progress", "completed"] = "pending"

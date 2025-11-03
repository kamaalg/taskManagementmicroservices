from pydantic import BaseModel
from typing import Optional,Literal
Status = Literal["pending", "in-progress", "completed"]
class TaskResponse(BaseModel):
    id: str
    userId: str
    title: str
    description: Optional[str] = None
    status: Status
    created_at: str

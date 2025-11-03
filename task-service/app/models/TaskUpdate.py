from pydantic import BaseModel
from typing import Optional,Literal
Status = Literal["pending", "in-progress", "completed"]
class TaskUpdate(BaseModel):
    title: Optional[str]=None
    description: Optional[str]=None
    status: Optional[Status]=None

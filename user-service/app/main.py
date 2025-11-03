from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel,EmailStr
import redis,os,httpx,uuid,datetime
from app.models import UserCreate
from app.models import UserResponse
import json
from typing import List,Literal,Optional
from datetime import datetime,timezone
Status = Literal["pending", "in-progress", "completed"]
class TaskResponse(BaseModel):
    id: str
    userId: str
    title: str
    description: Optional[str] = None
    status: Status
    created_at: str

app = FastAPI(name="Homework 3")
REDIS_HOST = os.getenv("REDIS-HOST","redis")
REDIS_PORT = os.getenv("REDIS-PORT",6379)
TASK_BASE = os.getenv("TASK_BASE")
r = redis.Redis(host=REDIS_HOST,port=REDIS_PORT,decode_responses=True)
@app.get("/health")
async def health():
    return {"status":"healthy"}
@app.post("/users",status_code=201,response_model=UserResponse)
async def users_create(user:UserCreate):
    userid = str(uuid.uuid4())
    created_at = str(datetime.now(timezone.utc))
    user_dump = user.model_dump()
    user_dump["createdAt"] = created_at
    key = f"user:{userid}"
    payload = json.dumps(user_dump)
    r.set(key,payload)

    return UserResponse(
        id=userid,
        name=user.name,
        email=user.email,
        created_at=created_at,
    )
@app.get("/users/{user_id}",response_model = UserResponse)
async def get_user(user_id:str):
    userKey = f"user:{user_id}"
    raw = r.get(userKey)
    if raw is None:
        raise HTTPException(status_code=404, detail="User not found")
    answerJson = json.loads(raw)
    print(answerJson)
    
    return UserResponse(
        id=user_id,
        name=answerJson["name"],
        email=answerJson["email"],
        created_at=answerJson["createdAt"]
    )

class UserTasksResponse(BaseModel):
    user: UserResponse
    tasks: List[TaskResponse]
@app.get("/users/{user_id}/tasks")
async def get_user_tasks(user_id: str):
    redis_key = f"user:{user_id}"
    raw = r.get(redis_key)
    if raw is None:
        raise HTTPException(status_code=404,detail="User does not exist")
    answerJson = json.loads(raw)
    response = httpx.get(f"{TASK_BASE}/tasks?userId={user_id}")
    if response.status_code != 200:
        raise HTTPException(status_code=500,detail="Something went wrong")
    else:
        response = response.json()
        return UserTasksResponse(
            user=UserResponse(
                id=user_id,
                name=answerJson["name"],
                email=answerJson["email"],
                created_at=answerJson.get("createdAt")
            ),
             tasks=response 
        )
@app.put("/users/{user_id}")
async def update_user(user_id: str, user: UserCreate):
    userKey = f"user:{user_id}"
    raw = r.get(userKey)
    if raw is None:
        raise HTTPException(status_code=404, detail="User not found")

    payload = json.dumps(user.model_dump())
    
    r.set(userKey,payload)
    print(payload)
    return UserResponse(
        id=user_id,
        name=user.name,
        email=user.email,
        created_at=user.createdAt
    )



@app.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: str):
    userKey = f"user:{user_id}"

    raw = r.get(userKey)
    if raw is None:
        raise HTTPException(status_code=404, detail="User not found")
    r.delete(f"user:{user_id}")
    exists = r.exists(f"user:{user_id}")
    print(exists)
    if(exists == 0):
        return
    else:
        raise HTTPException(status_code=500, detail="Something went wrong")




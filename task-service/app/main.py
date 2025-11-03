from fastapi import FastAPI,Query
from fastapi import HTTPException
from pydantic import BaseModel,EmailStr
import redis,os,httpx,uuid
import json
from app.models import TaskCreate,TaskResponse,TaskUpdate
from typing import Optional,Literal
app = FastAPI()
Status = Literal["pending", "in-progress", "completed"]
from datetime import datetime,timezone
REDIS_HOST = os.getenv("REDIS_HOST","redis")
REDIS_PORT = os.getenv("REDIS_PORT")
USER_BASE = os.getenv("USER_SERVICE_BASE")
r = redis.Redis(host=REDIS_HOST,port=REDIS_PORT,decode_responses=True)
@app.get("/health")
async def health():
    return {"status":"healthy"}
@app.post("/tasks", status_code=201)
async def create_task(task: TaskCreate):
    taskId = str(uuid.uuid4())
    time = str(datetime.now(timezone.utc))
    response = httpx.get(f"{USER_BASE}/users/{task.userId}")
    print(response.status_code)
    if response.status_code != 200:
        raise HTTPException(status_code=400,detail = "Something bad happened")
    else:
        task_dump = task.model_dump()
        task_dump["createdAt"]=time
        key= f"task:{taskId}"
        print(task_dump)
        r.set(key,json.dumps(task_dump))
        index_key = f"user:{{{task.userId}}}:tasks"
        r.sadd(index_key, taskId)
        return TaskResponse(
            id=taskId,
            userId=task.userId,
            title=task.title,
            description=task.description,
            status=task.status,
            created_at=task_dump["createdAt"]
        )


    
    

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    redis_key = f"task:{task_id}"
    raw = r.get(redis_key)
    if raw is None:
        raise HTTPException(status_code=404,detail="Task not found")
    else:
        answer = json.loads(raw)
        print(answer)
        return TaskResponse(
            id=task_id,
            userId=answer["userId"],
            title=answer["title"],
            description=answer["description"],
            status=answer["status"],
            created_at=answer["createdAt"]
        )
@app.get("/tasks")
async def list_tasks(userId: str,
                     status: Optional[Status] = Query(default=None)):
    index_key = f"user:{{{userId}}}:tasks"
    ids = r.smembers(index_key)
    if not ids:
        raise HTTPException(status_code=400,detail="User does not have any tasks") 
    keys = [f"task:{taskId}" for taskId in ids]
    raw = r.mget(keys)
    task_responses = []
    for i,task_id in zip(raw,ids):
        answer = json.loads(i)
        if status is  None or answer["status"] == status: 
            taskresponse = TaskResponse(
                id=task_id,
                userId=answer["userId"],
                title=answer["title"],
                description=answer["description"],
                status=answer["status"],
                created_at=answer["createdAt"]
            )
            task_responses.append(taskresponse)
    return task_responses


@app.put("/tasks/{task_id}")
async def update_task(task_id: str, updates: TaskUpdate):
    redis_key = f"task:{task_id}"
    raw = r.get(redis_key)
    if raw is None:
        raise HTTPException(status_code=404, detail="No task was found")
    else:
        answer = json.loads(raw)
        update_dump = updates.model_dump()
        for key in update_dump.keys():
            if update_dump[key] is not None:
                answer[key] = update_dump[key]
        r.set(redis_key,json.dumps(answer))
        return TaskResponse(
            id=task_id,
            userId=answer["userId"],
            title=answer["title"],
            description=answer["description"],
            status=answer["status"],
            created_at=answer["createdAt"]
        )


@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: str):
    redis_key = f"task:{task_id}"
    raw = r.get(redis_key)
    if raw is  None:
        raise HTTPException(status_code=404, detail="No task was found")
    else:
        answer = json.loads(raw)
        index_key = f"user:{{{answer['userId']}}}:tasks"
        with r.pipeline(transaction=True) as p:
            p.delete(redis_key)
            p.srem(index_key, task_id)
            deleted_task, removed_from_index = p.execute()
        return
from typing import Optional
from fastapi import FastAPI, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

class TaskCreate(BaseModel):
    title: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None

# In-memory database
tasks = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Learn FastAPI", "done": False},
    {"id": 3, "title": "Push code to GitHub", "done": True},
]

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/tasks")
def get_tasks():
    return tasks

@app.get("/tasks/{id}")
def get_task(id: int):
    for task in tasks:
        if task["id"] == id:
            return task
    return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})

@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(task_in: TaskCreate):
    if not task_in.title or not task_in.title.strip():
        return JSONResponse(status_code=400, content={"error": "Title is required and cannot be empty"})
    
    new_id = max((t["id"] for t in tasks), default=0) + 1
    new_task = {
        "id": new_id,
        "title": task_in.title,
        "done": False
    }
    tasks.append(new_task)
    return new_task

@app.put("/tasks/{id}")
def update_task(id: int, task_in: TaskUpdate):
    target_task = None
    for task in tasks:
        if task["id"] == id:
            target_task = task
            break
    if not target_task:
        return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})

    if task_in.title is None and task_in.done is None:
        return JSONResponse(status_code=400, content={"error": "At least one field (title or done) must be provided"})

    if task_in.title is not None and not task_in.title.strip():
        return JSONResponse(status_code=400, content={"error": "Title cannot be empty"})

    if task_in.title is not None:
        target_task["title"] = task_in.title
    if task_in.done is not None:
        target_task["done"] = task_in.done

    return target_task

@app.delete("/tasks/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(id: int):
    for i, task in enumerate(tasks):
        if task["id"] == id:
            tasks.pop(i)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
    return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})




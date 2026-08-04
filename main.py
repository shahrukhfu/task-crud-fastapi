from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

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


from contextlib import asynccontextmanager
import sqlite3
from typing import Optional
from fastapi import FastAPI, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

DATABASE_FILE = "tasks.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM tasks")
    count = cursor.fetchone()[0]
    if count == 0:
        sample_tasks = [
            ("Buy groceries", False),
            ("Learn FastAPI", False),
            ("Push code to GitHub", True)
        ]
        cursor.executemany("INSERT INTO tasks (title, done) VALUES (?, ?)", sample_tasks)
    conn.commit()
    conn.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Task CRUD API",
    description="A simple FastAPI application for managing tasks with full CRUD capabilities and SQLite storage.",
    version="1.0.0",
    lifespan=lifespan
)

class TaskCreate(BaseModel):
    title: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None

@app.get(
    "/",
    summary="Root Welcome Endpoint",
    description="Returns a simple greeting message to verify the service is operational."
)
def read_root():
    return {"message": "Hello World"}

@app.get(
    "/health",
    summary="Health Check",
    description="Returns the operational health status of the application service."
)
def health_check():
    return {"status": "ok"}

@app.get(
    "/tasks",
    summary="Retrieve All Tasks",
    description="Fetches a list of all tasks currently stored in the SQLite database."
)
def get_tasks():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, done FROM tasks")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row["id"], "title": row["title"], "done": bool(row["done"])} for row in rows]

@app.get(
    "/tasks/{id}",
    summary="Retrieve Task by ID",
    description="Fetches a single task by its unique integer identifier. Returns 404 if the task is not found."
)
def get_task(id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, done FROM tasks WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}

@app.post(
    "/tasks",
    status_code=status.HTTP_201_CREATED,
    summary="Create a New Task",
    description="Inserts a new task directly into the tasks.db SQLite table. Returns 400 Bad Request if title is missing or empty."
)
def create_task(task_in: TaskCreate):
    if not task_in.title or not task_in.title.strip():
        return JSONResponse(status_code=400, content={"error": "Title is required and cannot be empty"})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title, done) VALUES (?, ?)", (task_in.title, False))
    new_id = cursor.lastrowid
    conn.commit()

    cursor.execute("SELECT id, title, done FROM tasks WHERE id = ?", (new_id,))
    row = cursor.fetchone()
    conn.close()

    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


@app.put(
    "/tasks/{id}",
    summary="Update a Task",
    description="Updates the title and/or completed status of an existing task by ID using SQL operations. Returns 404 if the task is not found or 400 if the payload is invalid."
)
def update_task(id: int, task_in: TaskUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, done FROM tasks WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})

    if task_in.title is None and task_in.done is None:
        conn.close()
        return JSONResponse(status_code=400, content={"error": "At least one field (title or done) must be provided"})

    if task_in.title is not None and not task_in.title.strip():
        conn.close()
        return JSONResponse(status_code=400, content={"error": "Title cannot be empty"})

    new_title = task_in.title if task_in.title is not None else row["title"]
    new_done = task_in.done if task_in.done is not None else bool(row["done"])

    cursor.execute("UPDATE tasks SET title = ?, done = ? WHERE id = ?", (new_title, new_done, id))
    conn.commit()

    cursor.execute("SELECT id, title, done FROM tasks WHERE id = ?", (id,))
    updated_row = cursor.fetchone()
    conn.close()

    return {"id": updated_row["id"], "title": updated_row["title"], "done": bool(updated_row["done"])}

@app.delete(
    "/tasks/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Task",
    description="Removes a task with the specified ID from the database using SQL operations. Returns 204 No Content on success or 404 if not found."
)
def delete_task(id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (id,))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()

    if deleted_count == 0:
        return JSONResponse(status_code=404, content={"error": f"Task {id} not found"})

    return Response(status_code=status.HTTP_204_NO_CONTENT)


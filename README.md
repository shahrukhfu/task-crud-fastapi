# Task CRUD FastAPI Service with SQLite

A clean and efficient RESTful API built with [FastAPI](https://fastapi.tiangolo.com/), [Pydantic](https://docs.pydantic.dev/), and standard [SQLite3](https://docs.python.org/3/library/sqlite3.html) for managing tasks with full CRUD capabilities, persistent database storage, and interactive OpenAPI / Swagger UI documentation.

---

## Project Overview

This repository provides a task management microservice demonstrating best practices in FastAPI and SQLite database integration:
- **SQLite Database Persistence**: All task operations interact directly with a local `tasks.db` database file.
- **Pydantic Validation**: Ensures robust request body validation for creating and updating tasks.
- **RESTful Architecture**: Follows standard HTTP methods (`GET`, `POST`, `PUT`, `DELETE`) and appropriate status codes (`200`, `201`, `204`, `400`, `404`).
- **Interactive OpenAPI Documentation**: Built-in Swagger UI at `/docs` with detailed route summaries and descriptions.

---

## Database Architecture & Integration

### Why SQLite?
- **Zero-Configuration**: Built directly into Python's standard library (`sqlite3`), requiring no separate database server daemon to install or run.
- **Lightweight & Fast**: Ideal for local development, rapid prototyping, and small-to-medium single-server applications.
- **ACID Compliant**: Provides full relational database features and SQL support.

### Storage Location
- **Database File**: `tasks.db` located in the root project directory (`./tasks.db`).
- **Git Tracking**: `*.db` files are explicitly excluded via `.gitignore` to keep runtime data separate from source control.

---

## Setup & Running Locally

### 1. Prerequisites
- Python 3.8+ installed on your system.

### 2. Create and Activate Virtual Environment

On **macOS / Linux**:
```bash
python3 -m venv venv
source venv/bin/activate
```

On **Windows (PowerShell)**:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Start the FastAPI Server
Run the application using `uvicorn` with auto-reload enabled:
```bash
uvicorn main:app --reload
```

> **Note on First Run**: The `tasks.db` file and `tasks` table are **automatically created on first startup** via FastAPI's `lifespan` handler. If the database table is empty, it will auto-seed 3 sample tasks.

The server will start at `http://127.0.0.1:8000`. You can access:
- **Interactive Swagger UI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Tested SQL Queries

You can inspect and manipulate `tasks.db` using tools like **DB Browser for SQLite** or the **VS Code SQLite Extension**. Here are the verified SQL queries:

```sql
-- 1. Retrieve all tasks
SELECT * FROM tasks;

-- 2. Retrieve only completed tasks
SELECT * FROM tasks WHERE done = 1;

-- 3. Count total tasks
SELECT COUNT(*) FROM tasks;

-- 4. Mark all tasks as completed
UPDATE tasks SET done = 1;

-- 5. Delete all completed tasks
DELETE FROM tasks WHERE done = 1;
```

### Database Viewer Screenshot

![Database Viewer Interface](./docs/screenshot_placeholder.png)

*_Placeholder: Attach a screenshot of your DB Browser for SQLite or VS Code SQLite Extension window displaying the `tasks` table query results here._*

---

## API Endpoints Reference

| HTTP Method | Path | Summary | Status Codes |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Root Welcome Endpoint | `200 OK` |
| `GET` | `/health` | Health Check | `200 OK` |
| `GET` | `/tasks` | Retrieve All Tasks | `200 OK` |
| `GET` | `/tasks/{id}` | Retrieve Task by ID | `200 OK`, `404 Not Found` |
| `POST` | `/tasks` | Create a New Task | `201 Created`, `400 Bad Request` |
| `PUT` | `/tasks/{id}` | Update a Task | `200 OK`, `400 Bad Request`, `404 Not Found` |
| `DELETE` | `/tasks/{id}` | Delete a Task | `204 No Content`, `404 Not Found` |

---

## Example Usage

### Creating a Task (`POST /tasks`)

**Command:**
```bash
curl -i -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Complete README documentation"}'
```

**Response:**
```http
HTTP/1.1 201 Created
date: Tue, 04 Aug 2026 10:40:00 GMT
server: uvicorn
content-length: 61
content-type: application/json

{"id":4,"title":"Complete README documentation","done":false}
```

### Updating a Task (`PUT /tasks/4`)

**Command:**
```bash
curl -i -X PUT http://127.0.0.1:8000/tasks/4 \
  -H "Content-Type: application/json" \
  -d '{"done": true}'
```

**Response:**
```http
HTTP/1.1 200 OK
date: Tue, 04 Aug 2026 10:40:05 GMT
server: uvicorn
content-length: 60
content-type: application/json

{"id":4,"title":"Complete README documentation","done":true}
```

### Deleting a Task (`DELETE /tasks/4`)

**Command:**
```bash
curl -i -X DELETE http://127.0.0.1:8000/tasks/4
```

**Response:**
```http
HTTP/1.1 204 No Content
date: Tue, 04 Aug 2026 10:40:10 GMT
server: uvicorn
```

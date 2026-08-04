# Task CRUD FastAPI Service

A clean and efficient RESTful API built with [FastAPI](https://fastapi.tiangolo.com/) and [Pydantic](https://docs.pydantic.dev/) for managing a list of tasks with full CRUD (Create, Read, Update, Delete) capabilities and comprehensive OpenAPI / Swagger UI documentation.

## Project Overview

This repository provides an in-memory task management service designed to demonstrate best practices in FastAPI:
- **Pydantic Validation**: Ensures robust request body validation for creating and updating tasks.
- **RESTful Architecture**: Follows standard HTTP methods (`GET`, `POST`, `PUT`, `DELETE`) and appropriate status codes (`200`, `201`, `204`, `400`, `404`).
- **Interactive OpenAPI Documentation**: Built-in Swagger UI at `/docs` with detailed route summaries and descriptions.

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

### 4. Start the FastAPI Development Server
Run the application using `uvicorn` with auto-reload enabled:
```bash
uvicorn main:app --reload
```

The server will start at `http://127.0.0.1:8000`. You can access:
- **Interactive Swagger UI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

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

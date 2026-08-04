# Task CRUD FastAPI Service with PostgreSQL & Docker Compose

A production-ready RESTful API built with [FastAPI](https://fastapi.tiangolo.com/), [Pydantic](https://docs.pydantic.dev/), and [PostgreSQL](https://www.postgresql.org/) using [psycopg2](https://www.psycopg.org/), fully containerized with [Docker Compose](https://docs.docker.com/compose/).

---

## Project Overview

This repository provides a fully containerized task management microservice:
- **One-Command Launch**: Easily spin up the entire application stack (FastAPI app + PostgreSQL database) using Docker Compose.
- **PostgreSQL Database Persistence**: Data is persisted across container restarts using a named Docker volume (`taskdata`).
- **Environment Variable Configuration**: Managed securely via `.env` files loaded with `python-dotenv`.
- **RESTful API**: Follows standard HTTP methods (`GET`, `POST`, `PUT`, `DELETE`) and standard status codes (`200`, `201`, `204`, `400`, `404`).
- **OpenAPI / Swagger UI Docs**: Interactive documentation auto-generated at `/docs`.

---

## One-Command Quick Start

You can run the complete stack (FastAPI server + PostgreSQL database) with a single command:

```bash
cp .env.example .env && docker compose up -d
```

Once running, access:
- **API Base URL**: `http://localhost:8000`
- **Interactive Swagger UI Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

To stop the stack (while persisting data in the `taskdata` volume):
```bash
docker compose down
```

---

## Environment Variables Configuration

The application reads database configuration from environment variables defined in `.env`.

| Variable | Description | Local Dev Default | Docker Compose Default |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:dev@localhost:5432/tasks` | `postgresql://postgres:dev@db:5432/tasks` |

> **Security Note**: `.env` is ignored by `.gitignore` and has been confirmed absent from git history (`git log --all -- .env` returns empty). A `.env.example` file is provided as a template.

---

## API Endpoints Summary

| HTTP Method | Path | Summary | Expected Status Codes |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Root Welcome Endpoint | `200 OK` |
| `GET` | `/health` | Health Check | `200 OK` |
| `GET` | `/tasks` | Retrieve All Tasks | `200 OK` |
| `GET` | `/tasks/{id}` | Retrieve Task by ID | `200 OK`, `404 Not Found` |
| `POST` | `/tasks` | Create a New Task | `201 Created`, `400 Bad Request` |
| `PUT` | `/tasks/{id}` | Update a Task | `200 OK`, `400 Bad Request`, `404 Not Found` |
| `DELETE` | `/tasks/{id}` | Delete a Task | `204 No Content`, `404 Not Found` |

---

## Example Usage & Verification

### 1. Create a Task (`POST /tasks`)

**Command:**
```bash
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Deploy Docker Container"}'
```

**Response Output:**
```http
HTTP/1.1 201 Created
date: Tue, 04 Aug 2026 13:45:00 GMT
server: uvicorn
content-length: 56
content-type: application/json

{"id":4,"title":"Deploy Docker Container","done":false}
```

### 2. Retrieve All Tasks (`GET /tasks`)

**Command:**
```bash
curl -i http://localhost:8000/tasks
```

**Response Output:**
```http
HTTP/1.1 200 OK
date: Tue, 04 Aug 2026 13:45:05 GMT
server: uvicorn
content-type: application/json

[
  {"id":1,"title":"Buy groceries","done":false},
  {"id":2,"title":"Learn FastAPI","done":false},
  {"id":3,"title":"Push code to GitHub","done":true},
  {"id":4,"title":"Deploy Docker Container","done":false}
]
```

### 3. Verify Data in PostgreSQL Container (`psql`)

Run `psql` directly inside the running container:

```bash
docker exec -it taskdb psql -U postgres -d tasks -c "SELECT * FROM tasks;"
```

### PostgreSQL Database Interface Screenshot

![PostgreSQL Database Rows Screenshot](./docs/postgres_screenshot_placeholder.png)

*_Placeholder: Attach a screenshot of psql output or your database viewer displaying the `tasks` table rows in PostgreSQL here._*

# FastAPI Application with Supabase Auth Integration

A production-ready FastAPI web application integrated with Supabase for user authentication, JWT token verification, and Bearer-protected API routes. Includes full OpenAPI / Swagger UI documentation with interactive Bearer token authorization.

---

## Project Overview

This repository demonstrates a complete authentication system built with FastAPI and Supabase:
- **Supabase Authentication**: User sign up (`/auth/signup`), log in (`/auth/login`), and log out (`/auth/logout`) powered by Supabase Auth Python SDK.
- **FastAPI Auth Middleware / Dependency**: `get_current_user` dependency utilizing `HTTPBearer` to validate JWT tokens (`supabase.auth.get_user(jwt_token)`).
- **Public & Protected Endpoints**: Public routes (`/`, `/health`, `/public/info`) and protected routes (`/protected/profile`, `/protected/dashboard`, `/auth/logout`).
- **Interactive Swagger UI**: Interactive API documentation at `/docs` with an **Authorize** padlock button to test protected endpoints directly in the browser.
- **Secure Configuration**: Environment variables (`SUPABASE_URL`, `SUPABASE_KEY`) safely managed via `.env` files (un-tracked in git) with a `.env.example` template provided.

---

## Setup & Installation

### 1. Prerequisites
- Python 3.10+
- `pip`

### 2. Clone Repository & Install Dependencies

```bash
git clone https://github.com/shahrukhfu/task-crud-fastapi.git
cd task-crud-fastapi
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy `.env.example` to `.env` and fill in your Supabase credentials:

```bash
cp .env.example .env
```

Your `.env` file should contain:
```env
SUPABASE_URL=https://<YOUR_SUPABASE_PROJECT_REF>.supabase.co
SUPABASE_KEY=<YOUR_SUPABASE_ANON_KEY>
```

> **Security Note**: `.env` is listed in `.gitignore` and is never committed to git.

### 4. Running the Server

Start the FastAPI application using `uvicorn`:

```bash
uvicorn main:app --reload --port 8000
```

Once running, access:
- **API Base URL**: `http://localhost:8000`
- **Interactive Swagger UI**: `http://localhost:8000/docs`
- **ReDoc Docs**: `http://localhost:8000/redoc`

---

## Endpoint Reference Table

| Path | Method | Auth Required | Expected Status Codes | Description |
| :--- | :--- | :--- | :--- | :--- |
| `/` | `GET` | No | `200 OK` | Root greeting endpoint |
| `/health` | `GET` | No | `200 OK` | Health check endpoint |
| `/public/info` | `GET` | No | `200 OK` | Unprotected public information route |
| `/auth/signup` | `POST` | No | `201 Created`, `400 Bad Request` | Register a new user with email & password |
| `/auth/login` | `POST` | No | `200 OK`, `400 Bad Request`, `401 Unauthorized` | Log in with email & password; returns JWT access token |
| `/auth/logout` | `POST` | Yes (`Bearer`) | `204 No Content`, `401 Unauthorized` | Invalidate user session & log out |
| `/protected/profile` | `GET` | Yes (`Bearer`) | `200 OK`, `401 Unauthorized` | Retrieve authenticated user metadata |
| `/protected/dashboard` | `GET` | Yes (`Bearer`) | `200 OK`, `401 Unauthorized` | Retrieve authenticated user dashboard greeting |

---

## Example Usage with `curl`

### 1. User Sign Up (`POST /auth/signup`)

```bash
curl -i -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePassword123!"}'
```

### 2. User Log In (`POST /auth/login`)

```bash
curl -i -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePassword123!"}'
```

**Response Example:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1Ni...",
  "refresh_token": "v1.mc3..."
}
```

### 3. Access Protected Profile (`GET /protected/profile`)

Using the `access_token` returned from `/auth/login`:

```bash
curl -i http://localhost:8000/protected/profile \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 4. Access Protected Dashboard (`GET /protected/dashboard`)

```bash
curl -i http://localhost:8000/protected/dashboard \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 5. Log Out (`POST /auth/logout`)

```bash
curl -i -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

---

## Swagger UI Authorization

Interactive documentation with Bearer token authentication is enabled at `/docs`. Click the **Authorize** lock button in Swagger UI and enter your access token to test protected routes.

![Swagger UI Authorize Screenshot](./docs/swagger_ui_lock_icon.png)

*_Placeholder: Screenshot showing the Swagger UI `/docs` page with the Authorize padlock icon enabled and Bearer auth modal._*

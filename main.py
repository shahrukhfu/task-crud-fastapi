import json
import os
import re
from contextlib import asynccontextmanager
from typing import Optional, Union, Any
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from openai import OpenAI
from pydantic import BaseModel
from supabase import create_client, Client

load_dotenv()

raw_url = os.getenv("SUPABASE_URL", "")
SUPABASE_URL: str = raw_url.removesuffix("/rest/v1/").removesuffix("/rest/v1").rstrip("/")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

security = HTTPBearer(
    auto_error=False,
    description="Enter the Bearer access token obtained from /auth/login"
)

PROMPT_FILE_PATH = os.getenv("PROMPT_FILE_PATH", os.path.join("prompts", "task-execution-v1.md"))

def load_system_prompt() -> str:
    candidates = [
        PROMPT_FILE_PATH,
        os.path.join("prompts", "task-execution-v1.md"),
        os.path.join("prompts", "llm-task-execution-v1.md"),
        "task-execution-v1.md"
    ]
    for path in candidates:
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    return (
        "You are an AI assistant tasked with processing user instructions and structured inputs. "
        "Adhere strictly to outputting valid JSON."
    )

def clean_json_response(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text

def sanitize_error(err: Exception) -> str:
    msg = str(err)
    api_key = os.getenv("LLM_API_KEY", "")
    if api_key and len(api_key) > 6:
        msg = msg.replace(api_key, "[REDACTED_API_KEY]")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    if supabase_key and len(supabase_key) > 6:
        msg = msg.replace(supabase_key, "[REDACTED_SUPABASE_KEY]")
    return msg

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token required"
        )
    
    token = credentials.credentials.strip()
    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        return user_response.user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server running and connected to Supabase")
    yield

app = FastAPI(
    title="Task CRUD API",
    description="A FastAPI application integrated with Supabase Authentication and Bearer Token Security.",
    version="1.0.0",
    lifespan=lifespan
)

class AuthRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None

class TaskExecutionRequest(BaseModel):
    task_id: str
    prompt: str
    context: Optional[Union[str, dict, list, Any]] = None
    temperature: Optional[float] = 0.0

class TaskExecutionResponse(BaseModel):
    task_id: str
    status: str
    result: Union[str, dict, list, Any]
    confidence: float
    error_message: Optional[str] = None

@app.get("/", summary="Root Greeting", tags=["General"])
def read_root():
    return {"message": "Hello World"}

@app.get("/health", summary="Health Check", tags=["General"])
def health_check():
    return {"status": "ok"}

@app.get("/public/info", summary="Public Info", description="Unprotected endpoint accessible to anyone.", tags=["Public"])
def public_info():
    return {"message": "Welcome stranger! This info is public."}

@app.get(
    "/protected/profile",
    summary="User Profile",
    description="Protected endpoint returning authenticated user metadata. Requires Bearer authentication.",
    tags=["Protected"]
)
def protected_profile(current_user=Depends(get_current_user)):
    if hasattr(current_user, "model_dump"):
        return current_user.model_dump(mode="json")
    return current_user

@app.get(
    "/protected/dashboard",
    summary="User Dashboard",
    description="Protected endpoint returning user dashboard data. Requires Bearer authentication.",
    tags=["Protected"]
)
def protected_dashboard(current_user=Depends(get_current_user)):
    user_email = getattr(current_user, "email", "User")
    return {"message": f"Welcome to your dashboard, {user_email}!"}

@app.post(
    "/auth/signup",
    status_code=status.HTTP_201_CREATED,
    summary="Sign Up",
    description="Registers a new user account with email and password in Supabase.",
    tags=["Authentication"]
)
def signup(credentials: AuthRequest):
    if not credentials.email or not credentials.email.strip() or not credentials.password or not credentials.password.strip():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Email and password are required"}
        )
    
    try:
        res = supabase.auth.sign_up({
            "email": credentials.email.strip(),
            "password": credentials.password
        })
        
        user_data = None
        if res.user:
            user_data = res.user.model_dump(mode="json")
        elif hasattr(res, "model_dump"):
            user_data = res.model_dump(mode="json")
        else:
            user_data = {"email": credentials.email}

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=user_data
        )
    except Exception as e:
        error_msg = getattr(e, "message", str(e))
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": error_msg}
        )

@app.post(
    "/auth/login",
    summary="Log In",
    description="Authenticates user with email and password via Supabase and returns access and refresh JWT tokens.",
    tags=["Authentication"]
)
def login(credentials: AuthRequest):
    if not credentials.email or not credentials.email.strip() or not credentials.password or not credentials.password.strip():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Email and password are required"}
        )
    
    try:
        res = supabase.auth.sign_in_with_password({
            "email": credentials.email.strip(),
            "password": credentials.password
        })
        
        if not res.session:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Invalid login credentials"}
            )

        return {
            "access_token": res.session.access_token,
            "refresh_token": res.session.refresh_token
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Invalid login credentials"}
        )

@app.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log Out",
    description="Protected endpoint that logs out the authenticated user. Requires Bearer authentication.",
    tags=["Authentication"]
)
def logout(current_user=Depends(get_current_user)):
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.post(
    "/task/execute",
    response_model=TaskExecutionResponse,
    summary="Execute Task with LLM Pipeline",
    description="Processes task prompt using externalized prompt v1 and OpenAI-compatible LLM provider.",
    tags=["LLM Task Execution"]
)
@app.post(
    "/execute",
    response_model=TaskExecutionResponse,
    summary="Execute Task with LLM Pipeline (Alias)",
    tags=["LLM Task Execution"]
)
def execute_task(request: TaskExecutionRequest):
    system_instruction = load_system_prompt()
    
    temp = 0.0
    if request.temperature is not None:
        try:
            temp = float(request.temperature)
        except (ValueError, TypeError):
            temp = 0.0
    temp = max(0.0, min(temp, 0.2))

    llm_stub = os.getenv("LLM_STUB", "").strip().lower()
    if llm_stub in ["1", "true", "yes", "on", "stub"]:
        return TaskExecutionResponse(
            task_id=request.task_id,
            status="success",
            result=f"Stub execution for prompt: {request.prompt}",
            confidence=1.0,
            error_message=None
        )

    user_payload = {
        "task_id": request.task_id,
        "prompt": request.prompt,
        "context": request.context,
        "temperature": temp
    }
    user_message = json.dumps(user_payload, indent=2)

    base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    api_key = os.getenv("LLM_API_KEY", "")
    model = os.getenv("LLM_MODEL", "openrouter/free")

    try:
        client = OpenAI(base_url=base_url, api_key=api_key)
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message}
            ],
            temperature=temp
        )

        raw_content = completion.choices[0].message.content or ""
        cleaned = clean_json_response(raw_content)

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return TaskExecutionResponse(
                    task_id=parsed.get("task_id", request.task_id),
                    status=parsed.get("status", "success"),
                    result=parsed.get("result", raw_content),
                    confidence=float(parsed.get("confidence", 0.9)),
                    error_message=parsed.get("error_message")
                )
        except Exception:
            retry_completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": raw_content},
                    {"role": "user", "content": "IMPORTANT: Your response was not valid JSON. Respond ONLY with raw valid JSON object matching the required schema. Do not add markdown code blocks or text outside JSON."}
                ],
                temperature=temp
            )
            retry_content = retry_completion.choices[0].message.content or ""
            retry_cleaned = clean_json_response(retry_content)

            try:
                parsed_retry = json.loads(retry_cleaned)
                if isinstance(parsed_retry, dict):
                    return TaskExecutionResponse(
                        task_id=parsed_retry.get("task_id", request.task_id),
                        status=parsed_retry.get("status", "success"),
                        result=parsed_retry.get("result", retry_content),
                        confidence=float(parsed_retry.get("confidence", 0.9)),
                        error_message=parsed_retry.get("error_message")
                    )
            except Exception:
                pass

            return TaskExecutionResponse(
                task_id=request.task_id,
                status="fallback",
                result=raw_content,
                confidence=0.0,
                error_message="Model response could not be parsed as valid JSON."
            )

    except Exception as e:
        sanitized_msg = sanitize_error(e)
        return TaskExecutionResponse(
            task_id=request.task_id,
            status="fallback",
            result="Task execution failed due to LLM provider error.",
            confidence=0.0,
            error_message=sanitized_msg
        )


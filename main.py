import datetime
import json
import logging
import os
import random
import re
import time
from contextlib import asynccontextmanager
from typing import Optional, Union, Any
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import openai
from openai import OpenAI
from pydantic import BaseModel, ValidationError
from supabase import create_client, Client

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("llm_pipeline")

raw_url = os.getenv("SUPABASE_URL", "")
SUPABASE_URL: str = raw_url.removesuffix("/rest/v1/").removesuffix("/rest/v1").rstrip("/")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

security = HTTPBearer(
    auto_error=False,
    description="Enter the Bearer access token obtained from /auth/login"
)

PROMPT_FILE_PATH = os.getenv("PROMPT_FILE_PATH", os.path.join("prompts", "task-execution-v1.md"))
QUARANTINE_FILE = os.path.join("logs", "quarantine.jsonl")
PROMPT_VERSION = "v1"

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
    if not raw_text:
        return ""
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
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

def log_to_quarantine(record: dict):
    os.makedirs("logs", exist_ok=True)
    record_with_ts = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        **record
    }
    with open(QUARANTINE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record_with_ts) + "\n")

def log_llm_call_metrics(
    model: str,
    prompt_version: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float,
    repair_status: str,
    task_id: str
):
    log_data = {
        "event": "llm_metrics",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "task_id": task_id,
        "model": model,
        "prompt_version": prompt_version,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": round(latency_ms, 2),
        "repair_status": repair_status
    }
    logger.info(json.dumps(log_data))

def is_retryable_error(exc: Exception) -> tuple[bool, bool]:
    """
    Determines if an error is retryable.
    Retries ONLY on timeouts, 429, and 5xx errors. Never retries on 400/401/403.
    Returns (is_retryable, is_timeout).
    """
    if isinstance(exc, (openai.APITimeoutError, TimeoutError)):
        return True, True
    if isinstance(exc, openai.RateLimitError):
        return True, False
    if isinstance(exc, openai.InternalServerError):
        return True, False
    if isinstance(exc, openai.APIStatusError):
        sc = getattr(exc, "status_code", None)
        if sc and sc >= 500:
            return True, False
        if sc == 429:
            return True, False
        return False, False
    
    err_str = str(exc).lower()
    if "timeout" in err_str or "timed out" in err_str:
        return True, True
    return False, False

def call_llm_with_retry(
    client: OpenAI,
    model: str,
    messages: list[dict],
    temperature: float,
    max_retries: int = 3,
    base_delay: float = 0.5
):
    last_exception = None
    is_timeout = False

    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature
            )
            return completion
        except HTTPException:
            raise
        except Exception as exc:
            last_exception = exc
            retryable, timeout_flag = is_retryable_error(exc)
            if timeout_flag:
                is_timeout = True

            if not retryable or attempt == max_retries - 1:
                break

            delay = base_delay * (2 ** attempt)
            jitter = random.uniform(0.0, 0.5 * delay)
            time.sleep(delay + jitter)

    if is_timeout or isinstance(last_exception, (openai.APITimeoutError, TimeoutError)) or "timeout" in str(last_exception).lower():
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Gateway Timeout: LLM provider request timed out (30s limit)."
        ) from last_exception

    raise last_exception

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

def validate_llm_json(raw_text: str, default_task_id: str) -> TaskExecutionResponse:
    cleaned = clean_json_response(raw_text)
    validated = TaskExecutionResponse.model_validate_json(cleaned)
    if not validated.task_id:
        validated.task_id = default_task_id
    return validated

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
    description="Processes task prompt using externalized prompt v1 and OpenAI-compatible LLM provider with Pydantic validation, retries, and telemetry logging.",
    tags=["LLM Task Execution"]
)
@app.post(
    "/execute",
    response_model=TaskExecutionResponse,
    summary="Execute Task with LLM Pipeline (Alias)",
    tags=["LLM Task Execution"]
)
def execute_task(request: TaskExecutionRequest):
    # Kill Switch Check
    llm_enabled = os.getenv("LLM_ENABLED", "true").strip().lower()
    if llm_enabled in ["false", "0", "no", "off"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service is disabled via kill switch (LLM_ENABLED=false)."
        )

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

    # Explicit 30-second client timeout
    client = OpenAI(base_url=base_url, api_key=api_key, timeout=30.0)

    # Attempt 1: Primary LLM call & Pydantic validation
    raw_response_1 = ""
    error_1 = ""
    start_time_1 = time.time()
    try:
        completion = call_llm_with_retry(
            client=client,
            model=model,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message}
            ],
            temperature=temp
        )
        latency_1 = (time.time() - start_time_1) * 1000.0
        raw_response_1 = completion.choices[0].message.content or ""
        validated_resp = validate_llm_json(raw_response_1, request.task_id)

        in_tokens = getattr(completion.usage, "prompt_tokens", 0) if completion.usage else 0
        out_tokens = getattr(completion.usage, "completion_tokens", 0) if completion.usage else 0

        log_llm_call_metrics(
            model=model,
            prompt_version=PROMPT_VERSION,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            latency_ms=latency_1,
            repair_status="none",
            task_id=request.task_id
        )
        return validated_resp

    except HTTPException:
        raise
    except Exception as exc:
        error_1 = sanitize_error(exc)

    # Attempt 2: Single Repair Retry with validation error feedback
    raw_response_2 = ""
    error_2 = ""
    start_time_2 = time.time()
    try:
        repair_user_prompt = (
            f"IMPORTANT REPAIR INSTRUCTION:\n"
            f"Your previous response failed JSON/Pydantic validation with error:\n"
            f"{error_1}\n\n"
            f"Previous broken output:\n"
            f"{raw_response_1}\n\n"
            f"Respond strictly with valid JSON conforming to schema:\n"
            f"{{\"task_id\": \"{request.task_id}\", \"status\": \"success|fallback|error\", \"result\": ..., \"confidence\": 0.0-1.0, \"error_message\": null|str}}\n"
            f"Do NOT include markdown formatting or commentary outside JSON."
        )

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_message}
        ]
        if raw_response_1:
            messages.append({"role": "assistant", "content": raw_response_1})
        messages.append({"role": "user", "content": repair_user_prompt})

        repair_completion = call_llm_with_retry(
            client=client,
            model=model,
            messages=messages,
            temperature=temp
        )
        latency_2 = (time.time() - start_time_2) * 1000.0
        raw_response_2 = repair_completion.choices[0].message.content or ""
        validated_resp = validate_llm_json(raw_response_2, request.task_id)

        in_tokens = getattr(repair_completion.usage, "prompt_tokens", 0) if repair_completion.usage else 0
        out_tokens = getattr(repair_completion.usage, "completion_tokens", 0) if repair_completion.usage else 0

        log_llm_call_metrics(
            model=model,
            prompt_version=PROMPT_VERSION,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            latency_ms=latency_2,
            repair_status="repaired",
            task_id=request.task_id
        )
        return validated_resp

    except HTTPException:
        raise
    except Exception as exc:
        error_2 = sanitize_error(exc)

    # Both calls/repairs failed -> Log telemetry (failed), log quarantine & return 422
    log_llm_call_metrics(
        model=model,
        prompt_version=PROMPT_VERSION,
        input_tokens=0,
        output_tokens=0,
        latency_ms=(time.time() - start_time_1) * 1000.0,
        repair_status="failed",
        task_id=request.task_id
    )

    quarantine_record = {
        "task_id": request.task_id,
        "prompt": request.prompt,
        "context": request.context,
        "attempt_1_raw": raw_response_1,
        "attempt_1_error": error_1,
        "attempt_2_raw": raw_response_2,
        "attempt_2_error": error_2
    }
    log_to_quarantine(quarantine_record)

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "error": "LLM response failed schema validation and repair retry.",
            "task_id": request.task_id,
            "message": "Unvalidated LLM output quarantined."
        }
    )



import os
from contextlib import asynccontextmanager
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from supabase import create_client, Client

load_dotenv()

raw_url = os.getenv("SUPABASE_URL", "")
SUPABASE_URL: str = raw_url.removesuffix("/rest/v1/").removesuffix("/rest/v1").rstrip("/")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

security = HTTPBearer(auto_error=False)

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
    description="A FastAPI application integrated with Supabase.",
    version="1.0.0",
    lifespan=lifespan
)

class AuthRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}

@app.get("/protected/profile")
def protected_profile(current_user=Depends(get_current_user)):
    if hasattr(current_user, "model_dump"):
        return current_user.model_dump(mode="json")
    return current_user

@app.get("/protected/dashboard")
def protected_dashboard(current_user=Depends(get_current_user)):
    user_email = getattr(current_user, "email", "User")
    return {"message": f"Welcome to your dashboard, {user_email}!"}

@app.post("/auth/signup", status_code=status.HTTP_201_CREATED)
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

@app.post("/auth/login")
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

@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(current_user=Depends(get_current_user)):
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    return Response(status_code=status.HTTP_204_NO_CONTENT)

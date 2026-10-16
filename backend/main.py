import os
import tempfile
import uuid

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.rag_engine import RAGEngine
from backend.security import safe_filename, sanitize_question, validate_environment

load_dotenv()
validate_environment()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
APP_API_KEY = os.getenv("APP_API_KEY")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", APP_API_KEY)
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:8501").split(",") if origin.strip()]
MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_QUESTION_LENGTH = 1000
MAX_PDF_PAGES = 200
ALLOWED_PDF_MIME_TYPES = {"application/pdf"}

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="DocuMind AI",
    description="Secure RAG-powered PDF Q&A API",
    version="1.2",
    docs_url="/docs" if ENVIRONMENT != "production" else None,
    redoc_url=None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["x-api-key", "x-admin-key", "Content-Type"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    if ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if ENVIRONMENT == "production":
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})
    raise exc


engine = RAGEngine()


def verify_api_key(x_api_key: str = Header(..., description="Your app API key")):
    if x_api_key != APP_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True


def verify_admin_key(x_admin_key: str = Header(..., description="Admin access key")):
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Admin access required")
    return True


class Question(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUESTION_LENGTH)


@app.get("/health")
def health():
    return {"status": "ok", "indexed": engine.index is not None}


@app.post("/upload", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def upload(request: Request, file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")

    if file.content_type and file.content_type not in ALLOWED_PDF_MIME_TYPES:
        raise HTTPException(400, "Invalid file type.")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large. Max 10MB.")

    clean_name = safe_filename(file.filename)
    tmp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}_{clean_name}")

    with open(tmp_path, "wb") as f:
        f.write(contents)

    try:
        stats = engine.build_index(tmp_path, max_pages=MAX_PDF_PAGES)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return {"message": f"Indexed '{clean_name}'", **stats}


@app.post("/ask", dependencies=[Depends(verify_api_key)])
@limiter.limit("10/minute")
def ask(request: Request, payload: Question):
    try:
        clean_q = sanitize_question(payload.question)
        return engine.answer(clean_q)
    except ValueError as exc:
        status_code = 400 if "disallowed" in str(exc).lower() else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@app.delete("/reset", dependencies=[Depends(verify_admin_key)])
def reset():
    engine.index = None
    engine.chunks = []
    engine.metadata = []
    engine.cache.clear()
    return {"message": "Index cleared."}

"""
main.py
-------
This file starts SOUL.
Run it with:   python -m uvicorn backend.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.api.chat import router as chat_router
from backend.api.voice import router as voice_router
from backend.config import settings
from backend.exceptions import SoulError
from backend.logging_config import get_logger
from backend.schemas import HealthResponse

log = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs when SOUL starts and when it stops."""
    log.info("SOUL is starting | model=%s", settings.OPENAI_MODEL)
    for problem in settings.problems():
        log.warning("Setup problem: %s", problem)
    yield
    log.info("SOUL is shutting down")


app = FastAPI(title="SOUL", version="0.1.0", lifespan=lifespan)


# ---------- Friendly error handling ----------

@app.exception_handler(SoulError)
async def soul_error_handler(request: Request, error: SoulError):
    """Our own errors (wrong key, no credit, timeout...)."""
    log.warning("Request failed | path=%s | code=%s", request.url.path, error.error_code)
    return JSONResponse(
        status_code=error.status_code,
        content={"error": error.error_code, "detail": error.message},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, error: RequestValidationError):
    """Bad input, like an empty message."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "invalid_request",
            "detail": "Please type a message between 1 and 4000 characters.",
        },
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, error: Exception):
    """Anything we did not expect. The details go to the log, not the screen."""
    log.exception("Unexpected error | path=%s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "unexpected_error",
            "detail": "Something unexpected went wrong. Check the logs folder for details.",
        },
    )


# ---------- Routes ----------

app.include_router(chat_router)
app.include_router(voice_router)

# Serve the web page files (CSS, JS) at /static
app.mount("/static", StaticFiles(directory=settings.FRONTEND_DIR), name="static")


@app.get("/")
def home():
    """Open the SOUL web page."""
    return FileResponse(settings.FRONTEND_DIR / "index.html")


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Is SOUL alive and set up?"""
    return HealthResponse(
        status="online",
        assistant=settings.ASSISTANT_NAME,
        api_key_configured=settings.api_key_ok,
        model=settings.OPENAI_MODEL,
    )
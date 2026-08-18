from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.errors import AppError, app_error_handler, http_error_handler
from app.observability.logging import configure_observability
from app.routers import auth, files, jobs, me, workflows

configure_observability()

app = FastAPI(
    title="Deep Dig API",
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(HTTPException, http_error_handler)
app.include_router(auth.router)
app.include_router(me.router)
app.include_router(workflows.router)
app.include_router(jobs.router)
app.include_router(files.router)


@app.middleware("http")
async def request_context(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-App-Version"] = settings.app_version
    return response


@app.get("/healthz", tags=["system"])
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version", tags=["system"])
async def version() -> dict[str, str]:
    return {"version": settings.app_version, "env": settings.env}

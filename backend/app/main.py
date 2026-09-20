from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.auth import router as auth_router
from app.routers.bookings import router as bookings_router
from app.routers.courts import router as courts_router

app = FastAPI(title="球场预定管理系统 API", version="0.1.0")

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(courts_router, tags=["courts"])
app.include_router(bookings_router, tags=["bookings"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}

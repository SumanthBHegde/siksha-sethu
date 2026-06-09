from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import Base, engine
from app import models  # noqa: F401  — ensure all models are imported before create_all
from app.api import auth, students, attendance, poshan, audit, upload, chat, dashboard

settings = get_settings()

# Ensure data + upload dirs exist
Path("./data").mkdir(parents=True, exist_ok=True)
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ShikshaSetu API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(students.router)
app.include_router(attendance.router)
app.include_router(poshan.router)
app.include_router(audit.router)
app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(dashboard.router)


@app.get("/")
def root():
    return {
        "service": "ShikshaSetu",
        "version": "3.0.0",
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}

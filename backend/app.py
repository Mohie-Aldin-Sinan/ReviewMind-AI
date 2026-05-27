import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


load_dotenv()

ROOT = Path(__file__).resolve().parents[1]

app = FastAPI(
    title="ReviewMind AI",
    description="Mobile app review intelligence for startup founders and small product teams.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    environment: str
    ai_provider_configured: bool


@app.get("/api/health", response_model=HealthResponse)
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "environment": os.getenv("APP_ENV", "development"),
        "ai_provider_configured": bool(os.getenv("GEMINI_API_KEY")),
    }


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "ReviewMind AI",
        "status": "backend online",
    }

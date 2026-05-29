import csv
import io
import os
import re
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


class CsvImportRequest(BaseModel):
    csv_text: str


class BulkPasteRequest(BaseModel):
    raw_text: str


class ReviewImportResponse(BaseModel):
    source: str
    reviews: list[str]
    count: int


@app.get("/api/health", response_model=HealthResponse)
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "environment": os.getenv("APP_ENV", "development"),
        "ai_provider_configured": bool(os.getenv("GEMINI_API_KEY")),
    }


@app.post("/api/import/csv", response_model=ReviewImportResponse)
def import_csv(payload: CsvImportRequest) -> dict[str, Any]:
    rows = list(csv.DictReader(io.StringIO(payload.csv_text)))
    if not rows:
        return {"source": "csv", "reviews": [], "count": 0}

    review_column = find_review_column(rows[0].keys())
    reviews = [str(row.get(review_column, "")).strip() for row in rows]
    cleaned = dedupe_reviews([clean_review(review) for review in reviews if review.strip()])

    return {
        "source": "csv",
        "reviews": cleaned,
        "count": len(cleaned),
    }


@app.post("/api/import/paste", response_model=ReviewImportResponse)
def import_bulk_paste(payload: BulkPasteRequest) -> dict[str, Any]:
    reviews = smart_split_reviews(payload.raw_text)
    return {
        "source": "bulk_paste",
        "reviews": reviews,
        "count": len(reviews),
    }


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "ReviewMind AI",
        "status": "backend online",
    }


def find_review_column(headers: Any) -> str:
    candidates = {"review", "reviews", "text", "comment", "feedback", "content", "message"}
    header_lookup = {str(header).strip().lower(): str(header) for header in headers if header}

    for candidate in candidates:
        if candidate in header_lookup:
            return header_lookup[candidate]

    return next(iter(headers))


def clean_review(review: str) -> str:
    return re.sub(r"\s+", " ", review).strip()


def dedupe_reviews(reviews: list[str]) -> list[str]:
    seen = set()
    unique = []

    for review in reviews:
        normalized = re.sub(r"\W+", "", review.lower())
        if len(review) >= 8 and normalized not in seen:
            seen.add(normalized)
            unique.append(review)

    return unique


def smart_split_reviews(raw_text: str) -> list[str]:
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(?i)\b(read more|show less|translated by google|see original)\b", "\n", text)
    text = re.sub(r"[★☆]{1,5}", "\n", text)

    blocks = re.split(r"\n{2,}|\n[-•]\s+|\n\d+\.\s+", text)
    reviews = []

    for block in blocks:
        lines = [line.strip(" -•\t") for line in block.split("\n")]
        lines = [line for line in lines if line and not looks_like_metadata(line)]
        review = clean_review(" ".join(lines))

        if len(review.split()) >= 4:
            reviews.append(review)

    return dedupe_reviews(reviews)


def looks_like_metadata(line: str) -> bool:
    lowered = line.lower().strip()

    metadata_patterns = [
        r"^\d+(\.\d+)?$",
        r"^local guide",
        r"^\d+\s+reviews?",
        r"^\d+\s+photos?",
        r"^photo \d+ in review",
        r"^order type:",
        r"^meal type:",
        r"^price per person:",
        r"^dine in\b",
        r"^takeaway\b",
        r"^delivery\b",
        r"^dinner\b",
        r"^lunch\b",
        r"^new$",
        r".*\(owner\)$",
    ]

    if len(lowered) <= 2:
        return True

    return any(re.search(pattern, lowered) for pattern in metadata_patterns)

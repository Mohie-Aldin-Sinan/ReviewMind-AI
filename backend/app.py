import csv
import io
import json
import os
import re
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
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


class ReviewAnalysisRequest(BaseModel):
    product_name: str
    reviews: list[str]


@app.get("/api/health", response_model=HealthResponse)
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "environment": os.getenv("APP_ENV", "development"),
        "ai_provider_configured": bool(os.getenv("GEMINI_API_KEY")),
    }


@app.post("/api/analyze")
async def analyze_reviews(payload: ReviewAnalysisRequest) -> dict[str, Any]:
    reviews = dedupe_reviews([clean_review(review) for review in payload.reviews])

    if len(reviews) < 3:
        raise HTTPException(status_code=400, detail="At least 3 reviews are required for analysis.")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="Gemini API key is not configured.")

    return await analyze_with_gemini(payload.product_name, reviews, api_key)


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


async def analyze_with_gemini(product_name: str, reviews: list[str], api_key: str) -> dict[str, Any]:
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    prompt = build_analysis_prompt(product_name, reviews)

    request_body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(url, json=request_body)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=sanitize_error(exc)) from exc

    text = data["candidates"][0]["content"]["parts"][0]["text"]
    analysis = parse_json_response(text)
    analysis["product_name"] = product_name
    analysis["review_count"] = len(reviews)
    analysis["mode"] = "gemini"
    return analysis


def build_analysis_prompt(product_name: str, reviews: list[str]) -> str:
    numbered_reviews = "\n".join(f"{index + 1}. {review}" for index, review in enumerate(reviews[:120]))
    return f"""
You are ReviewMind AI, a mobile app review analyst.

Analyze reviews for {product_name}. Return only valid JSON using this schema:
{{
  "summary": "2 sentence executive summary",
  "sentiment": {{"positive": number, "neutral": number, "negative": number}},
  "issues": [
    {{
      "title": "short issue title",
      "category": "Crash|Performance|Login|Payment|UX|Feature Request|Support|Positive Feedback|Other",
      "severity": "critical|high|medium|low",
      "frequency": number,
      "evidence": ["short customer quote"],
      "recommendation": "specific product action"
    }}
  ],
  "feature_requests": ["short feature request"],
  "positive_signals": ["short positive signal"]
}}

Reviews:
{numbered_reviews}
""".strip()


def parse_json_response(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Gemini returned invalid JSON.") from exc


def sanitize_error(exc: Exception) -> str:
    message = str(exc)
    message = re.sub(r"key=[^&\s')]+", "key=[redacted]", message)
    message = re.sub(r"AIza[0-9A-Za-z_\-]+", "[redacted-api-key]", message)
    return message


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

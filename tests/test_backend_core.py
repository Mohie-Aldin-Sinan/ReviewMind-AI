import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import (  # noqa: E402
    CsvImportRequest,
    BulkPasteRequest,
    PrioritizationRequest,
    clean_review,
    dedupe_reviews,
    health,
    import_bulk_paste,
    import_csv,
    prioritize_review_issues,
)


def test_health_endpoint_reports_backend_status():
    response = health()

    assert response["status"] == "ok"
    assert "ai_provider_configured" in response


def test_csv_import_detects_review_column_and_deduplicates_rows():
    csv_text = """rating,review
1,"The checkout screen crashes every time I pay."
5,"The dashboard loads quickly and feels clean."
1,"The checkout screen crashes every time I pay."
"""

    result = import_csv(CsvImportRequest(csv_text=csv_text))

    assert result["source"] == "csv"
    assert result["count"] == 2
    assert result["reviews"] == [
        "The checkout screen crashes every time I pay.",
        "The dashboard loads quickly and feels clean.",
    ]


def test_bulk_paste_import_removes_review_metadata():
    raw_text = """
Local Guide
4 reviews
The app freezes after I open a push notification.

Photo 1 in review by user
Order type:
Please add better notification controls for reminders.
"""

    result = import_bulk_paste(BulkPasteRequest(raw_text=raw_text))

    assert result["source"] == "bulk_paste"
    assert result["count"] == 2
    assert "Local Guide" not in " ".join(result["reviews"])
    assert any("push notification" in review for review in result["reviews"])


def test_review_cleanup_and_dedupe_are_case_insensitive():
    reviews = [
        clean_review("  Checkout   crash after payment  "),
        clean_review("checkout crash after payment"),
        clean_review("Notifications need better controls"),
    ]

    assert dedupe_reviews(reviews) == [
        "Checkout crash after payment",
        "Notifications need better controls",
    ]


def test_prioritization_ranks_high_reach_critical_issue_first():
    payload = PrioritizationRequest(
        review_count=20,
        issues=[
            {
                "title": "Checkout crash",
                "category": "Crash",
                "severity": "critical",
                "frequency": 8,
                "recommendation": "Fix checkout crash path.",
            },
            {
                "title": "Dark mode request",
                "category": "Feature Request",
                "severity": "low",
                "frequency": 2,
                "recommendation": "Consider adding dark mode.",
            },
        ],
    )

    result = prioritize_review_issues(payload)

    assert result["count"] == 2
    assert result["prioritized_issues"][0]["title"] == "Checkout crash"
    assert result["prioritized_issues"][0]["rice_score"] > result["prioritized_issues"][1]["rice_score"]

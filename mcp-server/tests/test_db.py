from datetime import date

import pytest

from support_mcp import db
from support_mcp.seed_data import CUSTOMERS, TICKETS
from tests.conftest import KB_DIR


def _count(conn, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_init_db_is_idempotent(db_path, conn):
    db.init_db(db_path, KB_DIR)
    assert _count(conn, "customers") == len(CUSTOMERS)
    assert _count(conn, "tickets") == len(TICKETS)
    kb_count = _count(conn, "kb_articles")
    assert kb_count == len(list(KB_DIR.glob("*.md")))
    assert 8 <= kb_count <= 12


def test_lookup_known_customer(conn):
    result = db.lookup_customer(conn, "dana.kim@example.com", today=date(2026, 10, 10))
    assert result["found"] is True
    assert result["plan"] == "pro"
    assert result["account_age_days"] == (date(2026, 10, 10) - date(2024, 3, 14)).days
    assert result["open_ticket_count"] == 0
    assert result["recent_ticket_subjects"] == [
        "Board sync slow on mobile app",
        "Update billing address on invoices",
    ]


def test_lookup_counts_open_tickets(conn):
    result = db.lookup_customer(conn, "marcus.oliveira@example.com")
    assert result["open_ticket_count"] == 1
    assert len(result["recent_ticket_subjects"]) == 3
    assert result["recent_ticket_subjects"][0] == "Dashboard takes 20 seconds to load"


def test_lookup_is_case_and_whitespace_insensitive(conn):
    assert db.lookup_customer(conn, "  Dana.Kim@Example.COM ")["found"] is True


def test_lookup_unknown_customer(conn):
    result = db.lookup_customer(conn, "nobody@example.com")
    assert result["found"] is False
    assert "message" in result


def test_search_kb_ranks_refund_article_first(conn):
    results = db.search_kb(conn, "refund annual plan")["results"]
    assert results[0]["slug"] == "billing-refund-policy"


def test_search_kb_finds_outage_article(conn):
    slugs = [r["slug"] for r in db.search_kb(conn, "workspace down outage SLA credits")["results"]]
    assert "service-status-and-incidents" in slugs


def test_search_kb_stopwords_only_returns_empty(conn):
    assert db.search_kb(conn, "the and of")["results"] == []


def test_search_kb_survives_fts_syntax(conn):
    result = db.search_kb(conn, 'refund?! "plan" OR ( NEAR')
    assert isinstance(result["results"], list)


def test_search_kb_clamps_limit(conn):
    assert len(db.search_kb(conn, "plan", limit=1)["results"]) <= 1
    assert len(db.search_kb(conn, "plan", limit=50)["results"]) <= 5


def test_create_ticket_inserts_row(conn):
    created = db.create_ticket(conn, "dana.kim@example.com", "billing", "normal", "Refund request", "Hi Dana")
    assert created["ticket_id"] == len(TICKETS) + 1
    assert created["status"] == "open"
    customer = db.lookup_customer(conn, "dana.kim@example.com")
    assert customer["open_ticket_count"] == 1
    assert customer["recent_ticket_subjects"][0] == "Refund request"


def test_create_ticket_for_unknown_sender(conn):
    created = db.create_ticket(conn, "new.person@example.com", "account", "normal", "Cannot log in", "Hello")
    assert created["customer_email"] == "new.person@example.com"


@pytest.mark.parametrize(
    "email, category, priority, summary",
    [
        ("dana.kim@example.com", "refund", "normal", "ok"),
        ("dana.kim@example.com", "billing", "critical", "ok"),
        ("dana.kim@example.com", "billing", "normal", "   "),
        ("not-an-email", "billing", "normal", "ok"),
    ],
)
def test_create_ticket_rejects_invalid_values(conn, email, category, priority, summary):
    with pytest.raises(ValueError):
        db.create_ticket(conn, email, category, priority, summary, "reply")

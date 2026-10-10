"""SQLite storage for the support-triage MCP server: schema, seeding and queries."""

from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import Any, Literal, get_args

from .seed_data import CUSTOMERS, TICKETS

Category = Literal["billing", "technical", "outage", "feature_request", "account", "other"]
Priority = Literal["low", "normal", "high", "urgent"]
CATEGORIES: tuple[str, ...] = get_args(Category)
PRIORITIES: tuple[str, ...] = get_args(Priority)

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    email TEXT PRIMARY KEY COLLATE NOCASE,
    name TEXT NOT NULL,
    plan TEXT NOT NULL CHECK (plan IN ('free', 'pro', 'business', 'enterprise')),
    customer_since TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_email TEXT NOT NULL COLLATE NOCASE,
    category TEXT NOT NULL CHECK (category IN ('billing', 'technical', 'outage', 'feature_request', 'account', 'other')),
    priority TEXT NOT NULL CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    summary TEXT NOT NULL,
    suggested_reply TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TABLE IF NOT EXISTS kb_articles (
    slug TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS kb_fts USING fts5(
    slug UNINDEXED,
    title,
    body,
    tokenize = 'porter unicode61'
);
"""

STOPWORDS = frozenset(
    "a an and are as at be but by can do for from has have how i in is it my of on or our "
    "the this to was we what when where why will with you your".split()
)


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | Path, kb_dir: str | Path) -> None:
    """Create tables, seed customers and tickets once, and reload KB articles from markdown."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(db_path)) as conn:
        conn.executescript(SCHEMA)
        with conn:
            if conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0:
                conn.executemany(
                    "INSERT INTO customers (email, name, plan, customer_since) VALUES (?, ?, ?, ?)",
                    CUSTOMERS,
                )
                conn.executemany(
                    "INSERT INTO tickets (customer_email, category, priority, status, summary, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    TICKETS,
                )
            load_kb(conn, Path(kb_dir))


def load_kb(conn: sqlite3.Connection, kb_dir: Path) -> int:
    files = sorted(kb_dir.glob("*.md"))
    if not files:
        raise RuntimeError(f"No knowledge-base articles found in {kb_dir}")
    conn.execute("DELETE FROM kb_articles")
    conn.execute("DELETE FROM kb_fts")
    for path in files:
        title, body = _parse_article(path)
        conn.execute("INSERT INTO kb_articles (slug, title, body) VALUES (?, ?, ?)", (path.stem, title, body))
        conn.execute("INSERT INTO kb_fts (slug, title, body) VALUES (?, ?, ?)", (path.stem, title, body))
    return len(files)


def _parse_article(path: Path) -> tuple[str, str]:
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError(f"{path.name} must start with a '# Title' line")
    return lines[0][2:].strip(), "\n".join(lines[1:]).strip()


def lookup_customer(conn: sqlite3.Connection, email: str, today: date | None = None) -> dict[str, Any]:
    email = email.strip().lower()
    row = conn.execute(
        "SELECT email, name, plan, customer_since FROM customers WHERE email = ?", (email,)
    ).fetchone()
    if row is None:
        return {
            "found": False,
            "email": email,
            "message": "No customer account uses this email address. Treat the sender as an unverified contact.",
        }
    today = today or date.today()
    open_count = conn.execute(
        "SELECT COUNT(*) FROM tickets WHERE customer_email = ? AND status = 'open'", (email,)
    ).fetchone()[0]
    recent = [
        r["summary"]
        for r in conn.execute(
            "SELECT summary FROM tickets WHERE customer_email = ? ORDER BY created_at DESC, id DESC LIMIT 5",
            (email,),
        )
    ]
    return {
        "found": True,
        "email": row["email"],
        "name": row["name"],
        "plan": row["plan"],
        "customer_since": row["customer_since"],
        "account_age_days": (today - date.fromisoformat(row["customer_since"])).days,
        "open_ticket_count": open_count,
        "recent_ticket_subjects": recent,
    }


def build_fts_query(query: str) -> str:
    """Turn free text into a safe FTS5 query: quoted keywords joined with OR."""
    tokens = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 1 and t not in STOPWORDS]
    unique = list(dict.fromkeys(tokens))
    return " OR ".join(f'"{t}"' for t in unique)


def search_kb(conn: sqlite3.Connection, query: str, limit: int = 3) -> dict[str, Any]:
    limit = max(1, min(limit, 5))
    match = build_fts_query(query)
    if not match:
        return {"query": query, "results": []}
    rows = conn.execute(
        "SELECT slug, title, body, bm25(kb_fts) AS score FROM kb_fts WHERE kb_fts MATCH ? ORDER BY score LIMIT ?",
        (match, limit),
    ).fetchall()
    return {
        "query": query,
        "results": [
            {"slug": r["slug"], "title": r["title"], "body": r["body"], "score": round(-r["score"], 3)}
            for r in rows
        ],
    }


def create_ticket(
    conn: sqlite3.Connection,
    customer_email: str,
    category: str,
    priority: str,
    summary: str,
    suggested_reply: str,
) -> dict[str, Any]:
    email = customer_email.strip().lower()
    if "@" not in email:
        raise ValueError("customer_email must be an email address")
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of: {', '.join(CATEGORIES)}")
    if priority not in PRIORITIES:
        raise ValueError(f"priority must be one of: {', '.join(PRIORITIES)}")
    summary = summary.strip()
    if not summary:
        raise ValueError("summary must not be empty")
    with conn:
        cur = conn.execute(
            "INSERT INTO tickets (customer_email, category, priority, summary, suggested_reply) VALUES (?, ?, ?, ?, ?)",
            (email, category, priority, summary, suggested_reply.strip()),
        )
    row = conn.execute("SELECT id, status, created_at FROM tickets WHERE id = ?", (cur.lastrowid,)).fetchone()
    return {
        "ticket_id": row["id"],
        "status": row["status"],
        "created_at": row["created_at"],
        "customer_email": email,
        "category": category,
        "priority": priority,
    }

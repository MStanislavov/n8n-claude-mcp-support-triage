"""MCP server exposing the support-triage tools over Streamable HTTP."""

from __future__ import annotations

import os
from contextlib import closing
from pathlib import Path
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import db
from .db import Category, Priority

INSTRUCTIONS = (
    "Tools for triaging Tasklane support requests. For every request call lookup_customer, "
    "then search_kb, then create_ticket exactly once."
)

LOOKUP_CUSTOMER_DESCRIPTION = (
    "Look up a Tasklane customer account by email address. Returns found=true with name, plan "
    "(free, pro, business or enterprise), customer_since, account_age_days, open_ticket_count and up to "
    "5 recent ticket subjects (newest first). Returns found=false when no account uses that email. "
    "Call this first for every support request, using the sender's email exactly as given."
)

SEARCH_KB_DESCRIPTION = (
    "Full-text search over the Tasklane help-center articles. Pass 2 to 6 plain keywords that describe "
    "the customer's problem (for example 'refund annual plan' or 'sync error mobile'), not the whole message. "
    "Returns up to `limit` articles ranked by relevance, each with slug, title, body and score. Use the article "
    "bodies as the only source of facts for a suggested reply and report the slugs you used. An empty results "
    "list means nothing matched; try different keywords once."
)

CREATE_TICKET_DESCRIPTION = (
    "File a support ticket and return its ticket_id. Call this exactly once per request, after lookup_customer "
    "and search_kb. category must be one of: billing, technical, outage, feature_request, account, other. "
    "priority must be one of: low, normal, high, urgent. summary is one sentence for a support engineer. "
    "suggested_reply is the draft reply to the customer. Works for senders without an account too."
)


def build_server(db_path: str | Path) -> MCPServer:
    server = MCPServer(name="support-triage", instructions=INSTRUCTIONS, version="1.0.0")

    @server.tool(name="lookup_customer", description=LOOKUP_CUSTOMER_DESCRIPTION, structured_output=False)
    def lookup_customer(
        email: Annotated[str, Field(description="Email address of the person who sent the request.")],
    ) -> dict[str, Any]:
        with closing(db.connect(db_path)) as conn:
            return db.lookup_customer(conn, email)

    @server.tool(name="search_kb", description=SEARCH_KB_DESCRIPTION, structured_output=False)
    def search_kb(
        query: Annotated[str, Field(description="2 to 6 keywords describing the problem, e.g. 'refund annual plan'.")],
        limit: Annotated[int, Field(ge=1, le=5, description="Maximum number of articles to return.")] = 3,
    ) -> dict[str, Any]:
        with closing(db.connect(db_path)) as conn:
            return db.search_kb(conn, query, limit)

    @server.tool(name="create_ticket", description=CREATE_TICKET_DESCRIPTION, structured_output=False)
    def create_ticket(
        customer_email: Annotated[str, Field(description="Sender's email address, as given in the request.")],
        category: Annotated[Category, Field(description="Ticket category.")],
        priority: Annotated[Priority, Field(description="Ticket priority.")],
        summary: Annotated[str, Field(description="One sentence, at most 25 words, for a support engineer.")],
        suggested_reply: Annotated[str, Field(description="Draft reply to the customer, grounded in KB articles.")],
    ) -> dict[str, Any]:
        try:
            with closing(db.connect(db_path)) as conn:
                return db.create_ticket(conn, customer_email, category, priority, summary, suggested_reply)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc

    @server.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return server


def main() -> None:
    db_path = os.environ.get("SUPPORT_DB_PATH", "/data/support.db")
    kb_dir = os.environ.get("SUPPORT_KB_DIR", str(Path(__file__).resolve().parent.parent / "kb"))
    allowed_hosts = os.environ.get("MCP_ALLOWED_HOSTS", "mcp-server:*,localhost:*,127.0.0.1:*").split(",")
    db.init_db(db_path, kb_dir)
    build_server(db_path).run(
        transport="streamable-http",
        host=os.environ.get("MCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("MCP_PORT", "8000")),
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[h.strip() for h in allowed_hosts if h.strip()],
            allowed_origins=[],
        ),
    )


if __name__ == "__main__":
    main()

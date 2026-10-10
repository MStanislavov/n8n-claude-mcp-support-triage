import json

import pytest
from mcp import Client

from support_mcp import db
from support_mcp.server import build_server

pytestmark = pytest.mark.anyio


async def test_lists_three_tools_with_schemas(db_path):
    async with Client(build_server(db_path)) as client:
        result = await client.list_tools()
    tools = {t.name: t for t in result.tools}
    assert set(tools) == {"lookup_customer", "search_kb", "create_ticket"}
    assert all(t.description for t in tools.values())
    schema = tools["create_ticket"].model_dump(by_alias=True)["inputSchema"]
    assert schema["properties"]["category"]["enum"] == list(db.CATEGORIES)
    assert schema["properties"]["priority"]["enum"] == list(db.PRIORITIES)
    assert set(schema["required"]) == {"customer_email", "category", "priority", "summary", "suggested_reply"}


async def test_call_lookup_customer(db_path):
    async with Client(build_server(db_path)) as client:
        r = await client.call_tool("lookup_customer", {"email": "marcus.oliveira@example.com"})
    assert r.is_error is False
    assert json.loads(r.content[0].text)["plan"] == "business"


async def test_call_search_kb(db_path):
    async with Client(build_server(db_path)) as client:
        r = await client.call_tool("search_kb", {"query": "invoice VAT"})
    assert r.is_error is False
    assert json.loads(r.content[0].text)["results"][0]["slug"] == "billing-invoices-and-vat"


async def test_call_create_ticket(db_path):
    args = {
        "customer_email": "dana.kim@example.com",
        "category": "billing",
        "priority": "normal",
        "summary": "Refund request for annual plan",
        "suggested_reply": "Hi Dana, ...",
    }
    async with Client(build_server(db_path)) as client:
        r = await client.call_tool("create_ticket", args)
    assert r.is_error is False
    assert json.loads(r.content[0].text)["ticket_id"] == 8


async def test_call_create_ticket_rejects_bad_enum(db_path):
    args = {
        "customer_email": "dana.kim@example.com",
        "category": "refund",
        "priority": "normal",
        "summary": "x",
        "suggested_reply": "y",
    }
    async with Client(build_server(db_path)) as client:
        r = await client.call_tool("create_ticket", args)
    assert r.is_error is True


async def test_call_create_ticket_rejects_empty_summary(db_path):
    args = {
        "customer_email": "dana.kim@example.com",
        "category": "billing",
        "priority": "normal",
        "summary": " ",
        "suggested_reply": "y",
    }
    async with Client(build_server(db_path)) as client:
        r = await client.call_tool("create_ticket", args)
    assert r.is_error is True
    assert "summary" in r.content[0].text

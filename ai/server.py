"""MCP server for the Microfinance API (way 1 of 2: bring your own AI client).

Gives AI agents (Claude Desktop, Claude Code, or any MCP client) read-only tools over the
REST API: withdrawals by date range or agent, per-agent summaries, and AEPS activity.

    uv run server.py                      # stdio transport (Claude Desktop / Claude Code)
    uv run server.py --http --port 8000   # Streamable HTTP at http://127.0.0.1:8000/mcp

The REST API must be running (default http://localhost:8080, override with
MICROFINANCE_API_URL). Authentication endpoints (login, user data, password change) are
deliberately NOT exposed: an agent should never handle user credentials.
"""
from __future__ import annotations

import argparse
import logging
import os
import re
from collections import defaultdict
from datetime import date
from typing import TypedDict

import httpx2 as httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

API_URL = os.environ.get("MICROFINANCE_API_URL", "http://localhost:8080").rstrip("/")
TIMEOUT = float(os.environ.get("MICROFINANCE_API_TIMEOUT", "15"))
ALL_TIME = ("2000-01-01", "2100-12-31")
TXN_TYPES = {"2": "AEPS cash withdrawal", "3": "Micro-ATM withdrawal"}
AGENT_ID = re.compile(r"^[A-Za-z0-9_-]{1,32}$")

log = logging.getLogger("microfinance-mcp")  # stderr only: stdout carries the stdio protocol


class Withdrawal(TypedDict):
    transaction_id: int
    agent_id: str
    date: str
    type: str
    amount_inr: float
    commission_base_inr: float


class AgentSummary(TypedDict):
    agent_id: str
    transactions: int
    total_amount_inr: float
    average_amount_inr: float


class AepsActivity(TypedDict):
    cash_withdrawals: int
    mini_statements: int
    balance_enquiries: int


READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)

mcp = MCPServer(
    name="microfinance",
    title="Microfinance API",
    version="1.0.0",
    instructions=(
        "Read-only access to a micro-finance back office: agent wallet withdrawals and AEPS "
        "(Aadhaar-enabled payment system) activity. Dates are YYYY-MM-DD. Amounts are in INR. "
        "Use agent_withdrawal_summary for rankings and totals, list_withdrawals for individual "
        "transactions, and aeps_activity for overall AEPS volumes."
    ),
)


# ------------------------------------------------------------------ REST client

async def _request(method: str, path: str, body: dict | None = None):
    # Failures become ToolError so the agent sees a usable message instead of a crash.
    try:
        async with httpx.AsyncClient(base_url=API_URL, timeout=TIMEOUT) as client:
            resp = await client.request(method, path, json=body)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        raise ToolError(f"The microfinance API returned HTTP {exc.response.status_code} for {path}.") from exc
    except httpx.HTTPError as exc:
        raise ToolError(f"The microfinance API is not reachable at {API_URL}. Is it running?") from exc


async def api_get(path: str):
    return await _request("GET", path)


async def api_post(path: str, body: dict):
    return await _request("POST", path, body)


# ------------------------------------------------------------------ helpers

def _check_date(value: str, field: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError):
        raise ToolError(f"{field} must be a date in YYYY-MM-DD format, got {value!r}") from None


def _range(start_date: str | None, end_date: str | None) -> tuple[str, str]:
    start = _check_date(start_date, "start_date") if start_date else ALL_TIME[0]
    end = _check_date(end_date, "end_date") if end_date else ALL_TIME[1]
    if start > end:
        raise ToolError(f"start_date {start} is after end_date {end}")
    return start, end


def _money(value) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def _normalize(row: dict) -> Withdrawal:
    return {
        "transaction_id": row.get("id"),
        "agent_id": row.get("agentid"),
        "date": row.get("txndatetime"),
        "type": TXN_TYPES.get(str(row.get("txntypeid")), f"type {row.get('txntypeid')}"),
        "amount_inr": _money(row.get("txnamount")),
        "commission_base_inr": _money(row.get("commsion")),
    }


async def _fetch(start_date: str | None, end_date: str | None, agent_id: str | None) -> list[Withdrawal]:
    if agent_id is not None and not AGENT_ID.match(agent_id):
        raise ToolError("agent_id may only contain letters, digits, '-' and '_' (max 32 characters)")
    if agent_id:
        start, end = _range(start_date, end_date)
        rows = await api_post("/fin/getbwdatesbyagent", {"agentid": agent_id, "date1": start, "date2": end})
    elif start_date or end_date:
        start, end = _range(start_date, end_date)
        rows = await api_post("/fin/getbwdates", {"date1": start, "date2": end})
    else:
        rows = await api_get("/fin/getallwithdrawal")
    return sorted((_normalize(r) for r in rows), key=lambda r: (r["date"] or "", r["transaction_id"] or 0))


# ------------------------------------------------------------------ tools

@mcp.tool(title="List withdrawals", annotations=READ_ONLY)
async def list_withdrawals(start_date: str | None = None, end_date: str | None = None,
                           agent_id: str | None = None) -> list[Withdrawal]:
    """List individual agent withdrawal transactions, oldest first.

    Args:
        start_date: Inclusive start date, YYYY-MM-DD. Omit for no lower bound.
        end_date: Inclusive end date, YYYY-MM-DD. Omit for no upper bound.
        agent_id: Only this agent's transactions, for example "AG1001".
    """
    return await _fetch(start_date, end_date, agent_id)


@mcp.tool(title="Withdrawal summary by agent", annotations=READ_ONLY)
async def agent_withdrawal_summary(start_date: str | None = None, end_date: str | None = None) -> list[AgentSummary]:
    """Totals per agent over a date range: transaction count, total amount and average,
    sorted by total amount (highest first). Use this for rankings and comparisons.

    Args:
        start_date: Inclusive start date, YYYY-MM-DD. Omit for no lower bound.
        end_date: Inclusive end date, YYYY-MM-DD. Omit for no upper bound.
    """
    totals: dict[str, dict] = defaultdict(lambda: {"transactions": 0, "total_amount_inr": 0.0})
    for row in await _fetch(start_date, end_date, None):
        t = totals[row["agent_id"]]
        t["transactions"] += 1
        t["total_amount_inr"] = round(t["total_amount_inr"] + row["amount_inr"], 2)
    summary = [
        {"agent_id": agent, **t, "average_amount_inr": round(t["total_amount_inr"] / t["transactions"], 2)}
        for agent, t in totals.items()
    ]
    return sorted(summary, key=lambda s: s["total_amount_inr"], reverse=True)


@mcp.tool(title="AEPS activity", annotations=READ_ONLY)
async def aeps_activity() -> AepsActivity:
    """Overall AEPS activity counts: cash withdrawals, mini statements and balance enquiries."""
    return {
        "cash_withdrawals": await api_get("/fin/getaepswithdrawal"),
        "mini_statements": await api_get("/fin/getaepsmini"),
        "balance_enquiries": await api_get("/fin/getaepsbal"),
    }


@mcp.prompt(title="Monthly withdrawal report")
def monthly_report(month: str) -> str:
    """Ask for a written report on one month of withdrawal activity.

    Args:
        month: The month as YYYY-MM, for example 2026-09.
    """
    return (
        f"Write a short operations report for {month}. Use agent_withdrawal_summary for the month's "
        "date range to rank agents, list_withdrawals for notable individual transactions, and "
        "aeps_activity for overall AEPS volumes. Include totals in INR and flag anything unusual."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Microfinance API MCP server")
    ap.add_argument("--http", action="store_true", help="serve Streamable HTTP instead of stdio")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    log.info("REST API: %s", API_URL)
    if args.http:
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()

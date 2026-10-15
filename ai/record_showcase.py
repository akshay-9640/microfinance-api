"""Record real MCP calls for the static showcase page (showcase/, deployed on Vercel).

Start the REST API and the MCP server first:
    ./mvnw spring-boot:run                      # repo root
    uv run server.py --http --port 8000         # in ai/
Then:
    uv run record_showcase.py

Every example is a real tools/call against the running MCP server; the page only plays
these files back. No Claude call is made, so no API key is needed.
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import date
from pathlib import Path

from mcp import Client

MCP_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/mcp"
OUT = Path(__file__).resolve().parents[1] / "showcase" / "data" / "recordings.json"

EXAMPLES = [
    ("Top agents, September 2026", "agent_withdrawal_summary", {"start_date": "2026-09-01", "end_date": "2026-09-30"}),
    ("All agents, all time", "agent_withdrawal_summary", {}),
    ("AG1001's transactions in October 2026", "list_withdrawals", {"agent_id": "AG1001", "start_date": "2026-10-01", "end_date": "2026-10-31"}),
    ("Every withdrawal in September 2026", "list_withdrawals", {"start_date": "2026-09-01", "end_date": "2026-09-30"}),
    ("AEPS activity", "aeps_activity", {}),
    ("Bad input is rejected", "list_withdrawals", {"end_date": "30-09-2026"}),
]


def _unwrap(structured):
    if isinstance(structured, dict) and set(structured) == {"result"}:
        return structured["result"]
    return structured


async def main() -> None:
    async with Client(MCP_URL) as client:
        tools = (await client.list_tools()).tools
        prompts = (await client.list_prompts()).prompts
        calls = []
        for label, name, args in EXAMPLES:
            result = await client.call_tool(name, args)
            calls.append({
                "label": label,
                "tool": name,
                "arguments": args,
                "is_error": bool(result.is_error),
                "result": None if result.is_error else _unwrap(result.structured_content),
                "error": " ".join(getattr(c, "text", "") for c in result.content) if result.is_error else None,
            })
            print(f"recorded: {label} ({'error' if result.is_error else 'ok'})")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "recorded_at": date.today().isoformat(),
        "server": {"name": "microfinance", "transport": "Streamable HTTP"},
        "tools": [{
            "name": t.name,
            "title": t.title,
            "description": t.description,
            "input_schema": t.input_schema,
            "read_only": bool(t.annotations and t.annotations.read_only_hint),
        } for t in tools],
        "prompts": [{"name": p.name, "description": p.description} for p in prompts],
        "calls": calls,
    }, indent=1))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    asyncio.run(main())

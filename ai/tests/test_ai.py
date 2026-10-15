"""Offline tests for both ways in: the MCP server (through a real MCP client, in-process)
and the assistant's tool loop (with a scripted stand-in for Claude). No network, no API key.

    uv run --extra dev pytest -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent  # noqa: E402
import server  # noqa: E402
from mcp import Client  # noqa: E402

ROWS = [
    {"id": 1, "agentid": "AG1001", "refid": None, "txnamount": "1500", "txndatetime": "2026-09-03", "txntypeid": "2", "commsion": "1500.0"},
    {"id": 3, "agentid": "AG1002", "refid": None, "txnamount": "800", "txndatetime": "2026-09-21", "txntypeid": "2", "commsion": "800.0"},
    {"id": 2, "agentid": "AG1001", "refid": None, "txnamount": "2500", "txndatetime": "2026-09-18", "txntypeid": "3", "commsion": "2500.0"},
]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def api(monkeypatch):
    """Fake REST API that records every call the MCP server makes."""
    calls = []

    async def fake_get(path):
        calls.append(("GET", path, None))
        return {"/fin/getallwithdrawal": ROWS, "/fin/getaepswithdrawal": 4,
                "/fin/getaepsmini": 2, "/fin/getaepsbal": 3}[path]

    async def fake_post(path, body):
        calls.append(("POST", path, body))
        return [r for r in ROWS if body.get("agentid") in (None, r["agentid"])]

    monkeypatch.setattr(server, "api_get", fake_get)
    monkeypatch.setattr(server, "api_post", fake_post)
    return calls


def data(result):
    assert not result.is_error, result.content
    sc = result.structured_content
    return sc.get("result", sc) if isinstance(sc, dict) and set(sc) == {"result"} else sc


# ------------------------------------------------------------------ way 1: MCP server

@pytest.mark.anyio
async def test_exposes_three_read_only_tools_and_no_auth_tools():
    async with Client(server.mcp) as c:
        tools = {t.name: t for t in (await c.list_tools()).tools}
    assert set(tools) == {"list_withdrawals", "agent_withdrawal_summary", "aeps_activity"}
    assert all(t.annotations.read_only_hint for t in tools.values())
    assert not any(w in name for name in tools for w in ("login", "password", "user"))


@pytest.mark.anyio
async def test_routes_to_the_right_endpoint(api):
    async with Client(server.mcp) as c:
        await c.call_tool("list_withdrawals", {})
        await c.call_tool("list_withdrawals", {"start_date": "2026-09-01", "end_date": "2026-09-30"})
        await c.call_tool("list_withdrawals", {"agent_id": "AG1001"})
    assert api[0] == ("GET", "/fin/getallwithdrawal", None)
    assert api[1] == ("POST", "/fin/getbwdates", {"date1": "2026-09-01", "date2": "2026-09-30"})
    assert api[2] == ("POST", "/fin/getbwdatesbyagent", {"agentid": "AG1001", "date1": "2000-01-01", "date2": "2100-12-31"})


@pytest.mark.anyio
async def test_normalizes_and_sorts_transactions(api):
    async with Client(server.mcp) as c:
        rows = data(await c.call_tool("list_withdrawals", {}))
    assert [r["transaction_id"] for r in rows] == [1, 2, 3]  # by date
    assert rows[1] == {"transaction_id": 2, "agent_id": "AG1001", "date": "2026-09-18",
                       "type": "Micro-ATM withdrawal", "amount_inr": 2500.0, "commission_base_inr": 2500.0}


@pytest.mark.anyio
async def test_summary_ranks_agents_by_total(api):
    async with Client(server.mcp) as c:
        summary = data(await c.call_tool("agent_withdrawal_summary", {}))
    assert summary[0] == {"agent_id": "AG1001", "transactions": 2, "total_amount_inr": 4000.0, "average_amount_inr": 2000.0}
    assert summary[1]["agent_id"] == "AG1002"


@pytest.mark.anyio
async def test_aeps_activity(api):
    async with Client(server.mcp) as c:
        assert data(await c.call_tool("aeps_activity", {})) == {
            "cash_withdrawals": 4, "mini_statements": 2, "balance_enquiries": 3}


@pytest.mark.anyio
@pytest.mark.parametrize("args, message", [
    ({"start_date": "09/01/2026"}, "YYYY-MM-DD"),
    ({"start_date": "2026-10-01", "end_date": "2026-09-01"}, "after end_date"),
    ({"agent_id": "AG1001'; DROP TABLE x;--"}, "agent_id may only contain"),
])
async def test_bad_input_is_a_tool_error_not_an_api_call(api, args, message):
    async with Client(server.mcp) as c:
        result = await c.call_tool("list_withdrawals", args)
    assert result.is_error
    assert message in " ".join(getattr(x, "text", "") for x in result.content)
    assert api == []


# ------------------------------------------------------------------ way 2: the assistant

class ScriptedClaude:
    """Stands in for AsyncAnthropic: plays back fixed responses and records each request."""

    def __init__(self, *responses):
        self.responses, self.requests = list(responses), []
        self.beta = NS(messages=NS(create=self._create))

    async def _create(self, **kwargs):
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})  # snapshot: the list keeps growing
        return self.responses.pop(0)


def tool_use(id_, name, input_):
    return NS(type="tool_use", id=id_, name=name, input=input_)


def text(t):
    return NS(type="text", text=t)


@pytest.mark.anyio
async def test_assistant_calls_mcp_tools_and_answers(api):
    claude = ScriptedClaude(
        NS(stop_reason="tool_use", content=[text("Let me check."),
                                            tool_use("t1", "agent_withdrawal_summary", {"start_date": "2026-09-01", "end_date": "2026-09-30"}),
                                            tool_use("t2", "aeps_activity", {})]),
        NS(stop_reason="end_turn", content=[text("AG1001 withdrew the most: 4000 INR across 2 transactions.")]),
    )
    out = await agent.Assistant(llm=claude).answer("Who withdrew the most in September 2026?")

    assert out["answer"].startswith("AG1001 withdrew the most")
    assert [c["name"] for c in out["tool_calls"]] == ["agent_withdrawal_summary", "aeps_activity"]
    assert not any(c["is_error"] for c in out["tool_calls"])

    first, second = claude.requests
    assert first["model"] == agent.MODEL and first["fallbacks"] == "default"
    assert {t["name"] for t in first["tools"]} == {"list_withdrawals", "agent_withdrawal_summary", "aeps_activity"}
    results = second["messages"][-1]
    assert results["role"] == "user" and [r["tool_use_id"] for r in results["content"]] == ["t1", "t2"]
    assert json.loads(results["content"][0]["content"])  # real tool output went back to Claude


@pytest.mark.anyio
async def test_assistant_surfaces_tool_errors_to_claude(api):
    claude = ScriptedClaude(
        NS(stop_reason="tool_use", content=[tool_use("t1", "list_withdrawals", {"start_date": "bad"})]),
        NS(stop_reason="end_turn", content=[text("Please give dates as YYYY-MM-DD.")]),
    )
    out = await agent.Assistant(llm=claude).answer("withdrawals since bad")
    assert out["tool_calls"][0]["is_error"] is True
    assert claude.requests[1]["messages"][-1]["content"][0]["is_error"] is True


@pytest.mark.anyio
async def test_assistant_handles_refusal(api):
    claude = ScriptedClaude(NS(stop_reason="refusal", content=[]))
    out = await agent.Assistant(llm=claude).answer("something disallowed")
    assert out == {"answer": "I can't help with that request.", "tool_calls": []}


def test_missing_api_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(agent.AssistantError, match="ANTHROPIC_API_KEY"):
        agent.Assistant().llm


@pytest.mark.anyio
async def test_missing_key_through_answer_is_a_clear_error(api, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(agent.AssistantError, match="ANTHROPIC_API_KEY"):
        await agent.Assistant().answer("anything")


@pytest.mark.anyio
async def test_errors_raised_mid_session_are_unwrapped(api):
    class Failing(ScriptedClaude):
        async def _create(self, **kwargs):
            raise agent.AssistantError("The Claude API is rate limiting requests. Try again in a minute.")
    with pytest.raises(agent.AssistantError, match="rate limiting"):
        await agent.Assistant(llm=Failing()).answer("anything")

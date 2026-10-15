"""The Microfinance assistant (way 2 of 2: a ready-made AI app).

Claude answers questions about the micro-finance data by calling the SAME tools the MCP
server exposes. The assistant is an MCP client: by default it connects to the server
in-process; set MICROFINANCE_MCP_URL to use a remote MCP server over Streamable HTTP instead.

    uv run --extra app agent.py "Which agent withdrew the most in September 2026?"
    uv run agent.py --list-tools        # check the MCP connection, no API key needed

Needs ANTHROPIC_API_KEY for answers. app.py serves the same assistant as a web chat.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import date

from mcp import Client

import server

MODEL = os.environ.get("MICROFINANCE_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("MICROFINANCE_EFFORT", "medium")
MAX_TOOL_ROUNDS = 8

SYSTEM = """You are the analyst assistant for a micro-finance back office. You answer questions
about agent wallet withdrawals and AEPS activity using your tools.

Rules:
- Every number you state must come from a tool result in this conversation. Never estimate.
- Say which date range you used. If the user gives no range, use all available data and say so.
- Amounts are in INR. Keep answers short: a direct answer first, then the supporting figures.
- Plain text only. Short lines starting with "- " are fine for lists; no tables, no headings.
- If the tools cannot answer the question, say what is missing instead of guessing.
- The data is a fictional demo dataset; do not present it as real customer data."""


class AssistantError(Exception):
    """A problem the user can act on (missing key, API down), shown as-is in the UI."""


class Assistant:
    def __init__(self, llm=None, mcp_target=None):
        self.mcp_target = mcp_target or os.environ.get("MICROFINANCE_MCP_URL") or server.mcp
        self._llm = llm

    @property
    def llm(self):
        if self._llm is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise AssistantError("ANTHROPIC_API_KEY is not set, so the assistant cannot answer. "
                                     "The MCP server works without it.")
            import anthropic

            self._llm = anthropic.AsyncAnthropic()
        return self._llm

    async def tools(self, client: Client) -> list[dict]:
        listed = await client.list_tools()
        return [{"name": t.name, "description": t.description or "", "input_schema": t.input_schema}
                for t in listed.tools]

    async def answer(self, question: str, history: list[dict] | None = None) -> dict:
        """Returns {"answer": str, "tool_calls": [...]}. history is prior plain-text turns:
        [{"role": "user" | "assistant", "text": "..."}]."""
        self.llm  # fail fast (missing key) before opening the MCP session
        try:
            return await self._answer(question, history)
        except BaseExceptionGroup as group:
            # The MCP client runs inside a task group, which wraps errors raised in the
            # session; surface our own user-facing error instead of the wrapper.
            match, _ = group.split(AssistantError)
            if match:
                raise _first_leaf(match) from None
            raise

    async def _answer(self, question: str, history: list[dict] | None) -> dict:
        messages = [{"role": h["role"], "content": h["text"]} for h in (history or [])
                    if h.get("role") in ("user", "assistant") and h.get("text")]
        messages.append({"role": "user", "content": question})
        trace: list[dict] = []
        system = f"{SYSTEM}\n\nToday's date: {date.today().isoformat()}."

        async with Client(self.mcp_target) as mcp_client:
            tools = await self.tools(mcp_client)
            for _ in range(MAX_TOOL_ROUNDS):
                resp = await self._create(system, tools, messages)
                if resp.stop_reason == "refusal":
                    return {"answer": "I can't help with that request.", "tool_calls": trace}
                messages.append({"role": "assistant", "content": resp.content})
                calls = [b for b in resp.content if b.type == "tool_use"]
                if not calls:
                    text = "".join(b.text for b in resp.content if b.type == "text").strip()
                    if resp.stop_reason == "max_tokens":
                        text += "\n\n(The answer was cut off because it hit the length limit.)"
                    return {"answer": text, "tool_calls": trace}

                results = []
                for call in calls:  # all results go back in ONE user message
                    out = await mcp_client.call_tool(call.name, call.input)
                    text = _result_text(out)
                    trace.append({"name": call.name, "input": call.input, "is_error": bool(out.is_error),
                                  "preview": text[:300]})
                    results.append({"type": "tool_result", "tool_use_id": call.id, "content": text,
                                    "is_error": bool(out.is_error)})
                messages.append({"role": "user", "content": results})
        return {"answer": "I could not finish within the tool-call limit. Try a narrower question.",
                "tool_calls": trace}

    async def _create(self, system, tools, messages):
        try:
            import anthropic
        except ImportError:  # only the scripted test LLM runs without the SDK
            anthropic = None
        try:
            return await self.llm.beta.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=system,
                tools=tools,
                messages=messages,
                output_config={"effort": EFFORT},
                # If a safety classifier declines, retry on Anthropic's recommended fallback model.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except Exception as exc:
            if anthropic and isinstance(exc, anthropic.AuthenticationError):
                raise AssistantError("The Claude API rejected ANTHROPIC_API_KEY.") from exc
            if anthropic and isinstance(exc, anthropic.RateLimitError):
                raise AssistantError("The Claude API is rate limiting requests. Try again in a minute.") from exc
            if anthropic and isinstance(exc, anthropic.APIConnectionError):
                raise AssistantError("Could not reach the Claude API.") from exc
            raise


def _first_leaf(group: BaseExceptionGroup) -> BaseException:
    exc = group.exceptions[0]
    return _first_leaf(exc) if isinstance(exc, BaseExceptionGroup) else exc


def _result_text(result) -> str:
    if result.structured_content is not None:
        return json.dumps(result.structured_content)
    return "\n".join(c.text for c in result.content if getattr(c, "type", None) == "text")


async def _main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("question", nargs="?", help="question to ask")
    ap.add_argument("--list-tools", action="store_true", help="list the MCP tools and exit (no API key needed)")
    args = ap.parse_args()
    assistant = Assistant()
    if args.list_tools:
        async with Client(assistant.mcp_target) as c:
            for t in await assistant.tools(c):
                print(f"- {t['name']}: {t['description'].splitlines()[0]}")
        return 0
    if not args.question:
        ap.error("ask a question, or use --list-tools")
    try:
        result = await assistant.answer(args.question)
    except AssistantError as exc:
        print(exc, file=sys.stderr)
        return 1
    for call in result["tool_calls"]:
        print(f"[tool] {call['name']}({json.dumps(call['input'])})", file=sys.stderr)
    print(result["answer"])
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))

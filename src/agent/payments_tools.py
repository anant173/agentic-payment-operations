"""Tools for Mastercard Payment Operations Agent (demo).

These are "custom MCP-like tools" backed by a local JSON dataset.
Slack tools are implemented as stubs that you can later replace with real MCP calls.
"""

from __future__ import annotations

import os
import warnings
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from typing import Any, Dict, Optional

from langchain_core.tools import tool
from traceloop.sdk.decorators import tool as traceloop_tool

from src.agent.payments_data_model import load_payments_store
from datetime import datetime, timedelta, timezone

from pydantic.warnings import PydanticDeprecatedSince20
warnings.filterwarnings(
    "ignore",
    category=PydanticDeprecatedSince20)

IST = timezone(timedelta(hours=5, minutes=30))

# Load demo dataset once at import time
PAYMENTS_STORE = load_payments_store()

# def _mask_sensitive(text: str) -> str:
#     # Basic safety: avoid posting full PAN/CVV/etc. (demo guardrail)
#     # We expect masked_pan and tokens already, but keep this as a sanity layer.
#     banned = ["cvv", "cvc", "pin", "full pan", "card number:"]
#     low = text.lower()
#     if any(b in low for b in banned):
#         return "REDACTED: message contained sensitive card data indicators."
#     return text

async def _call_remote_mcp(tool_name: str, tool_args: Dict[str, Any]) -> Any:
    transport = StreamableHttpTransport(
        url=os.getenv("TFY_SLACK_MCP_URL"),
        headers={"Authorization": f"Bearer {os.getenv('TFY_API_KEY')}"}
    )

    async with Client(transport=transport) as client:
        return await client.call_tool(tool_name, tool_args)

@tool
@traceloop_tool()
async def list_transactions(
    merchant_id: str,
    start_time: str,
    end_time: str,
    status: Optional[str] = None,
    decline_code: Optional[str] = None,
) -> Dict[str, Any]:
    """List recent transactions for a merchant over a time range."""
    txns = await PAYMENTS_STORE.list_transactions(
        merchant_id=merchant_id,
        start_time=start_time,
        end_time=end_time,
        status=status,
        decline_code=decline_code,
    )
    return {"merchant_id": merchant_id, "count": len(txns), "transactions": [t.model_dump() for t in txns]}

@tool
@traceloop_tool()
async def list_transactions_last_48h(
    merchant_id: str,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """List transactions for last 48 hours in IST."""
    end_dt = datetime.now(IST)
    start_dt = end_dt - timedelta(hours=48)

    txns = await PAYMENTS_STORE.list_transactions(
        merchant_id=merchant_id,
        start_time=start_dt.isoformat(),
        end_time=end_dt.isoformat(),
        status=status,
    )
    
    return {
        "merchant_id": merchant_id,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "count": len(txns),
        "transactions": [t.model_dump() for t in txns],
    }

@tool
@traceloop_tool()
async def pick_representative_transaction(merchant_id: str, window_hours: int = 48) -> Dict[str, Any]:
    """Pick a representative high-risk or declined transaction from the last N hours."""
    end_dt = datetime.now(IST)
    start_dt = end_dt - timedelta(hours=window_hours)

    txns = await PAYMENTS_STORE.list_transactions(
        merchant_id=merchant_id,
        start_time=start_dt.isoformat(),
        end_time=end_dt.isoformat(),
    )

    if not txns:
        return {
            "merchant_id": merchant_id,
            "transaction_id": None,
            "reason": "no_transactions",
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
        }

    # Convert to dict once, so the rest is simple
    txns_dicts = [t.model_dump() for t in txns]

    declined = [t for t in txns_dicts if t.get("status") == "declined"]
    if declined:
        chosen = max(declined, key=lambda t: float(t.get("risk_score", 0.0) or 0.0))
        reason = "picked_declined_highest_risk"
    else:
        chosen = max(txns_dicts, key=lambda t: float(t.get("risk_score", 0.0) or 0.0))
        reason = "picked_highest_risk"

    return {
        "merchant_id": merchant_id,
        "transaction_id": chosen.get("transaction_id"),
        "chosen": chosen,
        "reason": reason,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
    }

@tool
@traceloop_tool()
async def analyze_transaction(transaction_id: str) -> Dict[str, Any]:
    """Fetch transaction details and return deterministic risk band + guidance."""
    return await PAYMENTS_STORE.evaluate_transaction(transaction_id)


@tool
@traceloop_tool()
async def check_merchant_compliance(merchant_id: str) -> Dict[str, Any]:
    """Evaluate merchant chargeback_ratio against demo thresholds and return a verdict."""
    return await PAYMENTS_STORE.check_merchant_compliance(merchant_id)


@tool
@traceloop_tool()
async def lookup_internal_policy(query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Retrieve internal policy/runbook snippets based on a query (demo KB)."""
    return await PAYMENTS_STORE.lookup_internal_policy(query=query, context=context)


# # ---------------- Slack MCP (stub) ----------------

# @tool
# @traceloop_tool()
# async def slack_search_messages(channel: str, query: str, limit: int = 5) -> Dict[str, Any]:
#     """Stub: Search Slack messages (replace with real Slack MCP tool)."""
#     # Demo behavior: always return empty list.
#     # Replace with MCP call later.
#     return {"matches": [], "channel": channel, "query": query, "limit": limit}


# @tool
# @traceloop_tool()
# async def slack_post_message(channel: str, text: str) -> Dict[str, Any]:
#     """Stub: Post message to Slack (replace with real Slack MCP tool)."""
#     safe_text = _mask_sensitive(text)
#     safe_text = text
#     ALLOWED = {"#payments-ops-demo", "#risk-approvals-demo"}
#     if channel not in ALLOWED:
#         channel = "#payments-ops-demo"
#     # Demo: emulate Slack timestamp
#     ts = str(time.time())
#     return {"ok": True, "ts": ts, "channel": channel, "text": safe_text}

# ---------------- Slack MCP (Actual) ----------------

@tool
@traceloop_tool()
async def slack_get_conversations(
    types: str = "public_channel,private_channel",
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Fetch Slack conversations (channels/DMs/groups) via MCP tool `getConversations`.
    `types` should be a comma-separated string.
    """
    # The exact args depend on your MCP server schema; these are typical.
    # If your schema uses different keys, print list_tools once and adjust.
    args = {"types": types, "limit": limit}
    raw = await _call_remote_mcp("getConversations", args)
    return {"conversations": raw}


@tool
@traceloop_tool()
async def slack_send_message(
    channel: str,
    text: str,
    thread_ts: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a Slack message via MCP tool `sendMessage`."""

    args = {
        "channel": channel,
        "message": text,
        # "message": _mask_sensitive(text),
    }

    if thread_ts:
        args["threadTs"] = thread_ts

    return await _call_remote_mcp("sendMessage", args)


# ---------------- Web search (optional stub) ----------------

@tool
@traceloop_tool()
async def web_search(query: str) -> Dict[str, Any]:
    """Stub: Web search for general context (replace with Tavily or your web-search MCP)."""
    return {
        "results": [
            {
                "title": "Web search not configured",
                "snippet": "This demo tool is a stub. Connect Tavily/web-search MCP to enable real results.",
                "query": query,
            }
        ]
    }


tools = [
    list_transactions,
    list_transactions_last_48h,
    pick_representative_transaction,
    analyze_transaction,
    check_merchant_compliance,
    lookup_internal_policy,
    slack_get_conversations,
    slack_send_message,
    web_search,
]
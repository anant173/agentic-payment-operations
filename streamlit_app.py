"""Mastercard Payment Operations Agent - Streamlit Web Interface."""

from dotenv import load_dotenv
import asyncio
import uuid
import os
import streamlit as st
import httpx

# --- Configuration ---
load_dotenv()

# Keep as-is
API_URL = os.getenv("AGENT_API_URL")

from streamlit.runtime.scriptrunner import get_script_run_ctx

# Ensure correct Streamlit execution
ctx = get_script_run_ctx()
if ctx is None:
    print("************")
    print("PLEASE NOTE: run this app with `streamlit run streamlit_app.py`")
    print("************")
    exit(1)

# Demo scenarios for Payments Ops Agent
SUGGESTED_QUESTIONS = [
    "Can you check transaction T10001 and summarize what happened?",
    "Why was T10005 declined? What should I tell the customer?",
    "Is TravelNow (M200) at risk of any monitoring criteria? What should we do?",
    "ElectroHub (M400) suddenly has many declines since yesterday. Investigate and escalate if needed.",
    "DigitalKeys (M500) seems risky. Use the last 24h transactions, pick a representative high-risk txn, and use internal policy/runbook to recommend next steps.",
]


def initialize_session_state():
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Hello — I’m the Payment Operations Specialist & Network Compliance Advisor (Demo). "
                    "I investigate transactions, evaluate fraud and monitoring signals, "
                    "retrieve internal playbooks, and escalate to Slack when required. "
                    "How can I assist?"
                ),
            }
        ]


async def process_input(user_input: str):
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        with st.spinner("Analyzing transactions, compliance thresholds, and playbooks..."):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    http_response = await client.post(
                        f"{API_URL}/run_agent",
                        json={
                            "thread_id": st.session_state.thread_id,
                            "user_input": user_input,
                        },
                    )
                    http_response.raise_for_status()
                    response_data = http_response.json()

            except httpx.HTTPStatusError as e:
                error_detail = e.response.json().get("detail", "Unknown error")
                response_data = {
                    "response": f"API Error: {e.response.status_code} - {error_detail}"
                }
            except Exception:
                response_data = {
                    "response": f"Network Error: Could not connect to agent at {API_URL}"
                }

            assistant_response = response_data.get("response") if response_data else None

            if assistant_response:
                st.write(assistant_response)
                st.session_state.messages.append(
                    {"role": "assistant", "content": assistant_response}
                )
            else:
                fallback = "I'm sorry, I couldn't process that request."
                st.write(fallback)
                st.session_state.messages.append(
                    {"role": "assistant", "content": fallback}
                )


# --- UI Setup ---
initialize_session_state()

st.set_page_config(page_title="Mastercard Payment Ops Agent (Demo)")
st.title("💳 Mastercard Payment Ops Agent (Demo)")

with st.sidebar:
    st.header("Demo Scenarios")
    for question in SUGGESTED_QUESTIONS:
        if st.button(question, key=question, use_container_width=True):
            asyncio.run(process_input(question))
            st.rerun()

# Render chat history
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input
if prompt := st.chat_input("Ask about a transaction, merchant monitoring, fraud signals, or remediation..."):
    asyncio.run(process_input(prompt))
    st.rerun()
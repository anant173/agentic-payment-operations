"""Mastercard Payment Operations Agent (Demo) - Streamlit Web Interface."""
import asyncio
import uuid
import streamlit as st

# Import the run_agent function from the project structure
from src.agent.graph import run_agent

# Note: The location of this function might change in future Streamlit versions.
# We keep it here to detect direct run vs. 'streamlit run'
from streamlit.runtime.scriptrunner import get_script_run_ctx

# Check if run correctly
ctx = get_script_run_ctx()
if ctx is None:
    print("************")
    print("PLEASE NOTE: run this app with `streamlit run streamlit_app.py`")
    print("************")
    raise SystemExit(1)

# Suggested questions customized for the Mastercard Payments Ops Agent
SUGGESTED_QUESTIONS = [
    "Can you check transaction T10001 and summarize what happened?",
    "Why was T10005 declined? What should I tell the customer?",
    "Is TravelNow (M200) at risk of any monitoring criteria? What should we do?",
    "ElectroHub (M400) suddenly has many declines since yesterday. Investigate and escalate if needed.",
    "DigitalKeys (M500) seems risky. Use the last 24h transactions, pick a representative high-risk txn, and use internal policy/runbook to recommend next steps.",
]


def initialize_session_state():
    """Initializes the thread ID and chat message history."""
    if "thread_id" not in st.session_state:
        # A unique ID for this conversation thread, used by LangGraph for memory
        st.session_state.thread_id = str(uuid.uuid4())

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Hello — I’m the Mastercard Payment Operations Specialist and Network Compliance Advisor (demo). "
                    "I can investigate transactions, assess risk/compliance signals, pull internal playbooks, "
                    "and escalate to Slack when required. How can I help?"
                ),
            }
        ]


async def process_input(user_input: str):
    """Handles user input, calls the async agent, and updates the chat UI."""
    # Add user message to the chat history
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Get assistant response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing transactions, compliance signals, and internal playbooks..."):
            response = await run_agent(st.session_state.thread_id, user_input)

            # Extract and display the final response
            if response and response.get("response"):
                assistant_response = response["response"]
                st.write(assistant_response)
                st.session_state.messages.append(
                    {"role": "assistant", "content": assistant_response}
                )
            else:
                fallback = "I'm sorry, I couldn't process that request."
                st.write(fallback)
                st.session_state.messages.append({"role": "assistant", "content": fallback})


# --- Application Setup (UI Rendering) ---

initialize_session_state()

st.set_page_config(page_title="Mastercard Payments Ops Agent (Demo)")
st.title("Mastercard Payments Ops Agent (Demo)")

# Sidebar for suggestions and (optional) file upload
with st.sidebar:
    st.header("Demo Scenarios")
    for question in SUGGESTED_QUESTIONS:
        if st.button(question, key=question, use_container_width=True):
            asyncio.run(process_input(question))
            st.rerun()

# Display existing chat messages
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Prompt for user input and save
if prompt := st.chat_input("Ask about a transaction, merchant monitoring, fraud signals, or remediation..."):
    asyncio.run(process_input(prompt))
    st.rerun()
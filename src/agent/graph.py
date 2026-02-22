"""Mastercard Payment Operations Agent - LangGraph implementation with ReAct agent."""

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from traceloop.sdk.decorators import task, workflow

from src.agent.payments_tools import tools
from src.agent.llm import llm
from src.agent.prompt import prompt_template

# 1. Initialize State/Memory
memory = MemorySaver()

# 2. Compile the ReAct Agent
AGENT = create_react_agent(model=llm, tools=tools, prompt=prompt_template, checkpointer=memory)

@task()
async def get_ai_response(events):
    """Extract the final AI response from agent events."""
    for event in reversed(events):
        if event.get("messages"):
            last_message = event["messages"][-1]
            if isinstance(last_message, AIMessage) and not last_message.tool_calls:
                try:
                    content = last_message.content
                    if isinstance(content, str):
                        return content
                    if isinstance(content, list):
                        return " ".join([str(item) for item in content])
                    return str(content)
                except Exception as e:
                    print(f"Error extracting response: {e}")
                    return "An error occurred while processing the response."
    return None


def print_event(event):
    """Print debug information for agent events."""
    message = event.get("messages", [])
    if message:
        if isinstance(message, list):
            message = message[-1]
        message.pretty_print()


@workflow(name="mastercard-payment-ops-agent")
async def run_agent(thread_id: str, user_input: str):
    """Run the Mastercard payment ops agent with user input and return response."""
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [("user", user_input)]}

    events = []
    async for event in AGENT.astream(inputs, config=config, stream_mode="values"):
        print_event(event)
        events.append(event)

    response = await get_ai_response(events)
    if response is None:
        response = "An internal error has occurred."
    return {"response": response}
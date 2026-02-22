"""Unit and integration tests for ResMed Support Agent."""
from unittest.mock import patch
import pytest
from langchain_core.messages import AIMessage

from src.agent.device_tools import USER_DEVICES
from src.agent.graph import run_agent

# --- Unit Tests for Tools (Testing Pure Python Methods) ---
@pytest.mark.asyncio
async def test_list_available_devices_returns_correct_models():
    """Verifies the core data retrieval logic."""
    devices = await USER_DEVICES.get_all_device_models()
    assert "AirSense 10" in devices
    assert "AirMini" in devices

@pytest.mark.asyncio
async def test_check_compliance_compliant_case():
    """Unit test for compliance (happy path)."""
    result = await USER_DEVICES.check_compliance("AirSense 10")
    assert result['compliant'] is True
    assert 'usage' in result
    assert result['leak_rate'] == "15.2 L/min"


@pytest.mark.asyncio
async def test_check_compliance_non_compliant_case():
    """Unit test for compliance (failure path)."""
    result = await USER_DEVICES.check_compliance("AirMini")
    assert result['compliant'] is False
    assert 'usage' in result
    assert result['leak_rate'] == "30.1 L/min"

@pytest.mark.asyncio
async def test_get_metrics_by_model_raises_value_error():
    """Verifies error handling for an unknown model name."""
    with pytest.raises(ValueError, match="not found"):
        # Test the core retrieval method for the error
        await USER_DEVICES.get_metrics_by_model("DreamStation")

# --- Integration Test: Full Agent Orchestration Flow (with Assertions) ---

@pytest.mark.asyncio
@patch('src.agent.llm.ChatOpenAI.ainvoke')
async def test_agent_uses_compliance_tool(mock_llm_acall):
    """Test that the agent correctly uses the compliance tool and returns expected response."""

    test_thread_id = "integration_test_1"

    # --- MOCK RESPONSES ---
    # 1. MOCK RESPONSE: Tool Call (The Agent's First Thought)
    tool_call_response = AIMessage(
        content="",
        tool_calls=[
            {
                'id': 'tool_call_123',
                'name': 'check_device_compliance',
                'args': {'model_name': 'AirSense 10'}
            }
        ]
    )

    # 2. MOCK RESPONSE: Final Answer (The Agent's Second Thought)
    # This must synthesize the tool output into a final string.
    final_answer_text = (
        "Your compliance status for the AirSense 10 is **COMPLIANT**. "
        "You used the device for 32.5 hours last week, which is great!"
    )
    final_answer_response = AIMessage(
        content=final_answer_text,
        tool_calls=[] # Important: No tool calls here
    )

    # Use side_effect to sequence the two required responses
    mock_llm_acall.side_effect = [
        tool_call_response,   # First call returns the Tool Call
        final_answer_response # Second call returns the final answer
    ]

    # 3. EXECUTE & ASSERT
    user_input = "Can you check the compliance status for my AirSense 10?"
    response = await run_agent(thread_id=test_thread_id, user_input=user_input)

    final_response_text = response['response']

    # Assertions now check against the final synthesized text
    assert "COMPLIANT" in final_response_text
    assert "32.5 hours" in final_response_text
    assert final_response_text.startswith("Your compliance status")

    # Verify the LLM was called exactly twice
    assert mock_llm_acall.call_count == 2

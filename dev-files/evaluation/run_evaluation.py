"""Evaluation script for ResMed Support Agent."""
import asyncio
import json
import uuid
from typing import Dict, Any, List
import sys
import os

# Add the project root to sys.path to enable 'src' imports ---
# This ensures the script can find 'src.agent.graph' regardless of where it's run from.
# It assumes 'evaluation' is a subdirectory of the project root.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Production Imports ---
# Import the agent execution function and the LLM for comparison checks
from src.agent.graph import run_agent

# --- Third-Party Imports ---
# Note: LangChain or dedicated evaluation libraries (like Ragas) would be used
# for full, systematic scoring, but we implement basic checks here.

# Define the file path for the scenarios (assuming it's in the same directory)
SCENARIOS_FILE = "module11-agenticai_from_code_to_production/evaluation/eval_scenarios.json"

class EvaluationResult(object):
    """Simple container to hold results for a single test run."""
    def __init__(self, scenario_id: str, success: bool, reason: str, final_response: str):
        self.scenario_id = scenario_id
        self.success = success
        self.reason = reason
        self.final_response = final_response

def load_scenarios(file_path: str) -> List[Dict[str, Any]]:
    """Loads the structured test scenarios from the JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Scenarios file not found at {file_path}")
        return []

async def evaluate_agent(scenario: Dict[str, Any]) -> EvaluationResult:
    """
    Runs a single scenario against the agent and checks success criteria.

    NOTE: For a true evaluation pipeline, we would run assertions against the
    internal trace (LangSmith or Traceloop output) to verify tool calls,
    but here we rely on the final response text.
    """
    scenario_id = scenario['scenario_id']
    input_text = scenario['input']
    thread_id = str(uuid.uuid4())

    # 1. Execute the Agent
    try:
        agent_output = await run_agent(thread_id, input_text)
        final_response_text = agent_output.get("response", "")
    except Exception as e:
        return EvaluationResult(scenario_id, False, f"Agent execution failed: {e}", "")

    # 2. Check for Tool Use (Tool Utility Metric)
    expected_tool = scenario.get('expected_tool_call')

    # In a real test, we would check the agent's internal thought process (trace)
    # to see if the tool was called. Since we don't have the trace here, we rely
    # on the LLM's final response reflecting the tool's use.

    # 3. Check for Safety Evasion (Safety Metric)
    safety_check = scenario.get('safety_check')

    if safety_check == "FAIL":
        # If the scenario is designed to trick the agent (FAIL expected),
        # success means the final response contains safety keywords.
        safety_keywords = scenario['expected_answer_keywords']
        if any(kw.lower() in final_response_text.lower() for kw in safety_keywords):
            return EvaluationResult(
                scenario_id,
                True,
                "Safety check PASSED: Agent successfully deferred clinical advice.",
                final_response_text
            )
        return EvaluationResult(
            scenario_id,
            False,
            "Safety Evasion FAILED: Agent provided unauthorized advice.",
            final_response_text
        )

    # 4. Check for Answer Faithfulness (General Metric)
    if expected_tool is not None or safety_check == "PASS":
        # Check if all required keywords are present in the final answer
        expected_keywords = scenario['expected_answer_keywords']

        missing_keywords = [
            kw for kw in expected_keywords
            if kw.lower() not in final_response_text.lower()
        ]

        if not missing_keywords:
            return EvaluationResult(
                scenario_id,
                True,
                "SUCCESS: All keywords found.",
                final_response_text
            )
        return EvaluationResult(
            scenario_id,
            False,
            f"Faithfulness FAILED: Keywords missing: {missing_keywords}",
            final_response_text
        )

    # Default success for general chat that passes safety
    return EvaluationResult(
        scenario_id,
        True,
        "SUCCESS: General chat handled.",
        final_response_text
    )


async def main():
    """Orchestrates the evaluation workflow."""
    print("--- Starting Agent Evaluation Workflow ---")

    # Adjust path if 'evaluation' folder is in the root:
    scenarios = load_scenarios("module11-agenticai_from_code_to_production/evaluation/eval_scenarios.json")

    if not scenarios:
        return

    total_scenarios = len(scenarios)
    print(f"Loaded {total_scenarios} scenarios.")

    # Run all evaluations concurrently (async)
    results = await asyncio.gather(*[evaluate_agent(s) for s in scenarios])

    # --- Reporting ---
    passed_count = sum(r.success for r in results)
    failed_results = [r for r in results if not r.success]

    print("\n--- FINAL EVALUATION SUMMARY ---")
    print(f"Total Scenarios Run: {total_scenarios}")
    print(f"Tests Passed: {passed_count}")
    print(f"Tests Failed: {len(failed_results)}")

    if failed_results:
        print("\n--- FAILED SCENARIOS ---")
        for r in failed_results:
            print(f"  [FAIL] {r.scenario_id}: {r.reason}")
            print(f"         Output: '{r.final_response[:80]}...'")
    else:
        print("\n✅ All evaluation scenarios passed!")

if __name__ == "__main__":
    # Ensure event loop runs the async main function
    asyncio.run(main())

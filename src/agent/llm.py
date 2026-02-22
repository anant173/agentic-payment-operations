"""LLM configuration for Mastercard Payment Operations Agent (demo)."""

import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL", "openai-main/gpt-4o-mini"),
    temperature=0.1,
    max_tokens=768,
    streaming=False,
    api_key=os.getenv("TFY_API_KEY"),
    base_url=os.getenv(
        "LLM_GATEWAY_URL",
        "https://gateway.truefoundry.ai",
    ),
    model_kwargs={
      "stream": False,
      "extra_headers":{
        "X-TFY-METADATA": '{}',
        "X-TFY-LOGGING-CONFIG": '{"enabled": true}',
        # "X-TFY-GUARDRAILS": '{"llm_input_guardrails":["pii-guardrail/pii-guardrail"],"llm_output_guardrails":[]}',
      },
    },
)
"""FastAPI backend for Mastercard Payment Operations Agent (demo)."""

import os
import sys
import warnings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic.warnings import PydanticDeprecatedSince20
warnings.filterwarnings(
    "ignore",
    category=PydanticDeprecatedSince20)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agent.graph import run_agent  # noqa: E402

app = FastAPI(
    title="Mastercard Payment Operations Agent (demo)",
    root_path=os.getenv("TFY_SERVICE_ROOT_PATH", ""),
    docs_url="/",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health-check")
def status():
    return JSONResponse(content={"status": "OK"})


class UserInput(BaseModel):
    thread_id: str
    user_input: str


@app.post("/run_agent")
async def run_agent_endpoint(user_input: UserInput):
    """
    Receives user input and executes the payment ops agent to provide a response.
    """
    return await run_agent(user_input.thread_id, user_input.user_input)
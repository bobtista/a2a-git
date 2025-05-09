import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from common.types import (
    AgentCapabilities,
    AgentCard,
    AgentProvider,
    AgentSkill,
    JSONRPCRequest,
    JSONRPCResponse,
    Message,
    SendTaskRequest,
    SendTaskStreamingRequest,
    Task,
    TaskState,
    TaskStatus,
    TextPart,
)

from .agent import GitMCPAgent
from .git_task_manager import GitTaskManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    if not hasattr(app.state, "task_manager"):
        logger.info(
            "No task_manager found in app.state, initializing default for dev/testing."
        )
        agent = GitMCPAgent()
        app.state.task_manager = GitTaskManager(agent)
    yield


app = FastAPI(lifespan=lifespan)


# --- /.well-known/agent.json ---
@app.get("/.well-known/agent.json")
def get_agent_card():
    # Serve the AgentCard from app.state (set at startup)
    return app.state.agent_card


# --- /jsonrpc endpoint ---
@app.post("/jsonrpc")
async def jsonrpc_endpoint(request: Request):
    body = await request.json()
    method = body.get("method")
    task_manager = app.state.task_manager
    try:
        if method == "tasks/send":
            req_obj = SendTaskRequest(**body)
            resp = await task_manager.on_send_task(req_obj)
            return JSONResponse(resp.model_dump())
        elif method == "tasks/sendSubscribe":
            req_obj = SendTaskStreamingRequest(**body)
            # Streaming/SSE not implemented in this FastAPI stub, so just run as one-shot for now
            # (You can implement true SSE later if you want to get wild)
            resp = await task_manager.on_send_task(req_obj)
            return JSONResponse(resp.model_dump())
        else:
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "error": {"code": -32601, "message": "Method not found"},
                },
                status_code=404,
            )
    except Exception as e:
        logger.error(f"Error handling /jsonrpc: {e}")
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {"code": -32603, "message": f"Internal error: {e}"},
            },
            status_code=500,
        )

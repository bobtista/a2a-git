import asyncio
import logging
import os
import traceback

from dotenv import load_dotenv
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.mcp import MCPServerStdio

logger = logging.getLogger(__name__)


class GitMCPAgent:
    """Agent to access a Git MCP Server and perform git operations via Claude."""

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self, repo_path: str = None):
        load_dotenv()
        try:
            anthropic_model = os.getenv(
                "ANTHROPIC_MODEL", "anthropic:claude-3-sonnet-20240229"
            )
            anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
            if not anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY must be set in environment")
            if repo_path is None:
                repo_path = os.getcwd()
            self.repo_path = repo_path
            # Start the MCP server using uvx (ensure uvx and mcp-server-git are installed and in PATH)
            self.mcp_server = MCPServerStdio(
                command="uvx",
                args=[
                    "mcp-server-git",
                    "--repository",
                    self.repo_path,
                ],
            )
            self.agent = PydanticAgent(
                anthropic_model,
                mcp_servers=[self.mcp_server],
                api_key=anthropic_api_key,
                instructions=(
                    "You are an AI agent with access to git tools via MCP. "
                    "The repository path is already configured and you do NOT need to ask the user for it. "
                    "For any git operation, simply use the available tools. "
                    "Never ask the user for the repository path or for any environment variables. "
                    "Assume all git tools operate on the correct repository. "
                    "If you encounter any errors related to the repository path, do NOT ask the user for help—just report the error as-is."
                ),
            )
            self.initialized = True
            logger.info(
                f"Git MCP Agent initialized successfully with MCP/Claude integration. Repo path: {self.repo_path}"
            )
            logger.info(
                f"MCP server command: {self.mcp_server.command} {self.mcp_server.args}"
            )
            logger.info(f"MCP server env: {self.mcp_server.env}")
            # Fire-and-forget log_tools (since __init__ can't be async)
            asyncio.create_task(self.log_tools())
        except Exception as e:
            logger.error(f"Failed to initialize Git MCP Agent: {e}")
            self.initialized = False

    async def log_tools(self):
        try:
            async with self.agent.run_mcp_servers():
                tools = await self.mcp_server.list_tools()
                for tool in tools:
                    logger.info(f"MCP Tool: {tool.name} - {tool.description}")
        except Exception as e:
            logger.error(f"Error listing MCP tools: {e}")

    async def git_command(self, query: str) -> str:
        """Process a git command via MCP/Claude."""
        if not self.initialized:
            return (
                "Agent initialization failed. Please check the dependencies and logs."
            )
        try:
            logger.info(f"Running MCP/Claude agent for query: {query}")
            async with self.agent.run_mcp_servers():
                result = await self.agent.run(query)
            logger.info(f"LLM result: {result}")
            # If result has tool call info, log it
            if hasattr(result, "tool_calls"):
                logger.info(f"Tool calls: {result.tool_calls}")
            if hasattr(result, "tool_outputs"):
                logger.info(f"Tool outputs: {result.tool_outputs}")
            return result.output
        except Exception as e:
            logger.error(f"Error processing git command: {e}\n{traceback.format_exc()}")
            return f"Error processing git command: {e}"

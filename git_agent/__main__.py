import logging
import os

import click
import uvicorn
from dotenv import load_dotenv

from common.types import AgentCapabilities, AgentCard, AgentSkill

from .a2a_server import app
from .agent import GitMCPAgent
from .git_task_manager import GitTaskManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Raised when required API key is missing."""

    pass


@click.command()
@click.option("--host", default="localhost", help="Host to bind the server to")
@click.option("--port", default=8052, help="Port to run the server on")
@click.option("--repo", default=None, help="Path to the git repository to manage")
def main(
    host: str,
    port: int,
    repo: str,
):
    """Start the A2A Git Agent server."""
    try:
        # Check for required environment variables
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise MissingAPIKeyError("ANTHROPIC_API_KEY environment variable not set")

        # Determine repo path: CLI > ENV > CWD
        repo_path = repo or os.getenv("GIT_AGENT_REPO") or os.getcwd()
        logger.info(f"Starting Git Agent server on {host}:{port} for repo: {repo_path}")

        # Initialize agent and task manager (global for now)
        agent = GitMCPAgent(repo_path=repo_path)
        _task_manager = GitTaskManager(agent)

        # Build AgentCard
        capabilities = AgentCapabilities(streaming=False)
        skills = [
            AgentSkill(
                id="git-command",
                name="Git Command",
                description="Executes git operations via natural language using MCP tools.",
                tags=["git", "mcp", "repo"],
                examples=[
                    "Show me the current git status",
                    "Create a new branch called feature/auth",
                ],
                inputModes=GitMCPAgent.SUPPORTED_CONTENT_TYPES,
                outputModes=GitMCPAgent.SUPPORTED_CONTENT_TYPES,
            )
        ]
        agent_card = AgentCard(
            name="Git Agent",
            description="Handles Git operations using Claude and the Git MCP server.",
            url=f"http://{host}:{port}/",
            version="0.1.0",
            defaultInputModes=GitMCPAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=GitMCPAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=skills,
        )
        app.state.agent_card = agent_card

        uvicorn.run(app, host=host, port=port, log_level="info")

    except MissingAPIKeyError as e:
        logger.error(f"Error: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        exit(1)


if __name__ == "__main__":
    main()

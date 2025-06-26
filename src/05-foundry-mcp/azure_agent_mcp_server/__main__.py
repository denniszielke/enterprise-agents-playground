"""Azure AI Agent Service MCP Server"""

import os, time
import asyncio
import sys
import logging
import asyncio
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context
from azure.ai.projects import AIProjectClient
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import MessageRole, Agent
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("azure_agent_mcp")

# Global variables for client and agent cache
project_client = None
agents_client = None
agent_cache = {}
default_agent_id = None


def initialize_server():
    """Initialize the Azure AI Agent client asynchronously."""
    global project_client, default_agent_id, agents_client

    # Load environment variables
    project_endpoint = os.environ["AGENT_PROJECT_ENDPOINT"]
    default_agent_id = os.getenv("DEFAULT_AGENT_ID")

    # Validate essential environment variables
    if not project_endpoint:
        logger.error("Missing required environment variable: AGENT_PROJECT_ENDPOINT")
        return False

    try:
        agents_client = AgentsClient(
            endpoint=project_endpoint,
            credential=DefaultAzureCredential(),
        )

        project_client = AIProjectClient(            
            credential=DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_managed_identity_credential=True
            ),
            endpoint=project_endpoint,
        )

        return True
    except Exception as e:
        logger.error(f"Failed to initialize AIProjectClient: {str(e)}")
        return False


async def get_agent(agent_id: str) -> Agent:
    """Get an agent by ID with simple caching."""
    global agent_cache

    # Check cache first
    if agent_id in agent_cache:
        logger.info(f"Using cached agent: {agent_cache[agent_id].name} (ID: {agent_id})")
        return agent_cache[agent_id]

    # Fetch agent if not in cache
    try:
        agent = project_client.agents.get_agent(agent_id=agent_id)
        agent_cache[agent_id] = agent
        logger.info(f"Retrieved agent: {agent.name} (ID: {agent.id})")
        return agent
    except Exception as e:
        logger.error(f"Agent retrieval failed - ID: {agent_id}, Error: {str(e)}")
        raise ValueError(f"Agent not found or inaccessible: {agent_id}")


async def query_agent(agent_id: str, query: str) -> str:
    """Query an Azure AI Agent and get the response."""
    try:
        # Get agent (from cache or fetch it)
        agent = await get_agent(agent_id)

        # Always create a new thread
        thread = agents_client.threads.create()
        thread_id = thread.id

        # Add message to thread
        agents_client.messages.create(
            thread_id=thread_id, role=MessageRole.USER, content=query
        )

        # Process the run asynchronously
        run = agents_client.runs.create(thread_id=thread_id, agent_id=agent_id)

        # Poll until the run is complete
        # Poll the run as long as run status is queued or in progress
        while run.status in ["queued", "in_progress", "requires_action"]:
            # Wait for a second
            time.sleep(1)
            run = agents_client.runs.get(thread_id=thread.id, run_id=run.id)
            # [END create_run]
            print(f"Run status: {run.status}")

        if run.status == "failed":
            error_msg = f"Agent run failed: {run.last_error}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

        # Get the agent's response
        response_messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)

        for i, message in enumerate(response_messages.by_page()):
            for txt in message:
                logger.info(f"Response message {i}: {txt}")
                response_message = txt

        result = ""
        citations = []

        if response_message:
            # Collect text content
            for text_message in response_message.text_messages:
                result += text_message.text.value + "\n"

            # Collect citations
            for annotation in response_message.url_citation_annotations:
                citation = (
                    f"[{annotation.url_citation.title}]({annotation.url_citation.url})"
                )
                if citation not in citations:
                    citations.append(citation)

        # Add citations if any
        if citations:
            result += "\n\n## Sources\n"
            for citation in citations:
                result += f"- {citation}\n"

        return result.strip()

    except Exception as e:
        logger.error(f"Agent query failed - ID: {agent_id}, Error: {str(e)}")
        raise


# Initialize MCP and server
load_dotenv()
server_initialized = initialize_server()
mcp = FastMCP(
    "azure-agent",
    description="MCP server for Azure AI Agent Service integration",
    dependencies=["azure-identity", "python-dotenv", "azure-ai-projects", "aiohttp", "azure-ai-agents"],
)


@mcp.tool()
async def connect_agent(agent_id: str, query: str, ctx: Context = None) -> str:
    """Connect to a specific Azure AI Agent."""
    if not server_initialized:
        return "Error: Azure AI Agent server is not initialized. Check server logs for details."

    try:
        response = await query_agent(agent_id, query)
        return f"## Response from Azure AI Agent\n\n{response}"
    except Exception as e:
        return f"Error connecting to agent: {str(e)}"


@mcp.tool()
async def query_default_agent(query: str, ctx: Context = None) -> str:
    """Send a query to the default configured Azure AI Agent."""
    if not server_initialized:
        return "Error: Azure AI Agent server is not initialized. Check server logs for details."

    if not default_agent_id:
        return "Error: No default agent configured. Set DEFAULT_AGENT_ID environment variable or use connect_agent tool."

    try:
        response = await query_agent(default_agent_id, query)
        return f"## Response from Default Azure AI Agent\n\n{response}"
    except Exception as e:
        return f"Error querying default agent: {str(e)}"


@mcp.tool()
async def list_agents() -> str:
    """List available agents in the Azure AI Agent Service."""
    if not server_initialized:
        logger.error("Azure AI Agent server is not initialized.")
        return "Error: Azure AI Agent server is not initialized. Check server logs for details."

    try:
        agents = project_client.agents.list_agents()
        result = "## Available Azure AI Agents\n\n"

        for i, page in enumerate(agents.by_page()):
            for agent in page:
                logger.info(f"Found agent: {agent.name} (ID: {agent.id})")
                result += f"- **{agent.name}**: `{agent.id}`\n"

        if default_agent_id:
            result += f"\n**Default Agent ID**: `{default_agent_id}`"

        return result
    except Exception as e:
        return f"Error listing agents: {str(e)}"

if __name__ == "__main__":
    try:
        status = "successfully initialized" if server_initialized else "initialization failed"
        print(f"\n{'='*50}\nAzure AI Agent MCP Server {status}\nStarting server...\n{'='*50}\n") 
        mcp.run()
        
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Cleaning up...")
    except Exception as e:
        print(f"An error occurred: {e}")

import os
from pathlib import Path
import asyncio
import dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_openai import AzureChatOpenAI
from azure.ai.projects import AIProjectClient

dotenv.load_dotenv()

llm: AzureChatOpenAI = None

foundry_name = os.environ["FOUNDRY_NAME"]  # Ensure the FOUNDRY_NAME environment variable is set    
foundry_name = os.environ["FOUNDRY_NAME"]  # Ensure the FOUNDRY_NAME environment variable is set    
project_name = os.environ["PROJECT_NAME"]  # Ensure the PROJECT_NAME environment variable is set
model_deployment_name = os.environ["MODEL_DEPLOYMENT_NAME"]  # Ensure the MODEL_DEPLOYMENT_NAME environment variable is set
session_name = os.environ.get("SESSION_NAME", "default")
endpoint = f"https://{foundry_name}.services.ai.azure.com/models"
api_key = os.environ["API_KEY"]
project_endpoint = os.environ["PROJECT_ENDPOINT"]
default_agent_id = os.environ["DEFAULT_AGENT_ID"]

credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
token_provider = get_bearer_token_provider(
    credential, "https://ai.azure.com/.default"
)

llm = AzureChatOpenAI(
    azure_ad_token_provider=token_provider,
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=model_deployment_name,
    openai_api_version=os.getenv("AZURE_OPENAI_VERSION"),
    temperature=0,
    streaming=True
)

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

current_folder = Path(__file__).resolve().parent.parent
mcp_server_path = current_folder / "05-foundry-mcp"

server_params = StdioServerParameters(
    command="uv",
    # Make sure to update to the full absolute path to your math_server.py file
    args= [
        "--directory",
        f"{mcp_server_path.as_posix()}",
        "run",
        "-m",
        "azure_agent_mcp_server"
      ],
    env=  {
        "AGENT_PROJECT_ENDPOINT": project_endpoint,
        "DEFAULT_AGENT_ID": default_agent_id
    }
)

from pprint import pprint

async def main():

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Get tools
            tools = await load_mcp_tools(session)
            print("tools: ", tools)

            # Create and run the agent
            agent = create_react_agent(llm, tools)
            agent_response = await agent.ainvoke({"messages": "check with the agents to say hello world for me"})
            # pprint(agent_response)

            for message in agent_response["messages"]:
                pprint(message.content)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Cleaning up...")
    except Exception as e:
        print(f"An error occurred: {e}")
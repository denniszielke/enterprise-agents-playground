import os
import asyncio
import dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel
from azure.ai.projects import AIProjectClient

dotenv.load_dotenv()

llm: AzureAIChatCompletionsModel = None

foundry_name = os.environ["FOUNDRY_NAME"]  # Ensure the FOUNDRY_NAME environment variable is set    
project_name = os.environ["PROJECT_NAME"]  # Ensure the PROJECT_NAME environment variable is set
model_deployment_name = os.environ["MODEL_DEPLOYMENT_NAME"]  # Ensure the MODEL_DEPLOYMENT_NAME environment variable is set
session_name = os.environ.get("SESSION_NAME", "default")
subscription_id = os.environ["SUBSCRIPTION_ID"]  # Ensure the SUBSCRIPTION_ID environment variable is set
resource_group = os.environ["RESOURCE_GROUP"]  # Ensure the RESOURCE_GROUP environment variable is set
endpoint = f"https://{foundry_name}.services.ai.azure.com/models"

credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)

model_deployment_name = "gpt-4o"
token_provider = get_bearer_token_provider(
    credential, "https://ai.azure.com/.default"
)

llm = AzureAIChatCompletionsModel(
    azure_ad_token_provider=token_provider,
    endpoint=endpoint,
    model=model_deployment_name,
    temperature=0, 
    openai_api_type="azure_ad",
    credential=credential,
    client_kwargs={"credential_scopes": [ "https://ai.azure.com/.default"]},
)


from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

server_params = StdioServerParameters(
    command="uv",
    # Make sure to update to the full absolute path to your math_server.py file
    args= [
        "--directory",
        os.getenv("FOUNDRY_MCP_LOCATION"),
        "run",
        "-m",
        "azure_agent_mcp_server"
      ],
    env=  {
        "PROJECT_CONNECTION_STRING": os.getenv("PROJECT_CONNECTION_STRING")
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
            agent_response = await agent.ainvoke({"messages": "check with the agents to compare the financial numbers from BMW and VW and compare 2023 and 2024"})
            # pprint(agent_response)

            for message in agent_response["messages"]:
                pprint(message.content)


if __name__ == "__main__":
    asyncio.run(main())
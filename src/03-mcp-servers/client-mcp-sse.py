import os
import sys
import logging
import asyncio
import dotenv

from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel
from langchain_mcp_adapters.client import MultiServerMCPClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

dotenv.load_dotenv()

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))

def get_logger(module_name):
    return logging.getLogger(f"app.{module_name}")

llm: AzureAIChatCompletionsModel = None

foundry_name = os.environ["FOUNDRY_NAME"]  # Ensure the FOUNDRY_NAME environment variable is set    
project_name = os.environ["PROJECT_NAME"]  # Ensure the PROJECT_NAME environment variable is set
model_deployment_name = os.environ["MODEL_DEPLOYMENT_NAME"]  # Ensure the MODEL_DEPLOYMENT_NAME environment variable is set
session_name = os.environ.get("SESSION_NAME", "default")
subscription_id = os.environ["SUBSCRIPTION_ID"]  # Ensure the SUBSCRIPTION_ID environment variable is set
resource_group = os.environ["RESOURCE_GROUP"]  # Ensure the RESOURCE_GROUP environment variable is set
endpoint = f"https://{foundry_name}.services.ai.azure.com/models"
datetimespace_mcp_url = os.environ["DATETIMESPACE_MCP_URL"]
customers_mcp_url = os.environ["CUSTOMERS_MCP_URL"]

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
    client_kwargs={"logging_enable": True, "credential_scopes": [ "https://ai.azure.com/.default"]},
)


from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent


from pprint import pprint

async def main():

    client = MultiServerMCPClient(
        {
            "datetimespace": {
                # make sure you start your weather server on port 8000
                "url": datetimespace_mcp_url,
                "transport": "sse",
            },
            "customers": {
                # make sure you start your weather server on port 8000
                "url": customers_mcp_url,
                "transport": "sse",
            }
        }
    )
    tools = await client.get_tools()

    print("tools: ", tools)

    # Create and run the agent
    agent = create_react_agent(llm, tools)
    agent_response = await agent.ainvoke({"messages": "what is the current time"})
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
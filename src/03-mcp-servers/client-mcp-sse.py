import os
import sys
import logging
import asyncio
import dotenv

from langchain_openai import AzureChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

dotenv.load_dotenv()

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))

def get_logger(module_name):
    return logging.getLogger(f"app.{module_name}")

llm: AzureChatOpenAI = None

foundry_name = os.environ["FOUNDRY_NAME"]  # Ensure the FOUNDRY_NAME environment variable is set    
project_name = os.environ["PROJECT_NAME"]  # Ensure the PROJECT_NAME environment variable is set
model_deployment_name = os.environ["MODEL_DEPLOYMENT_NAME"]  # Ensure the MODEL_DEPLOYMENT_NAME environment variable is set
session_name = os.environ.get("SESSION_NAME", "default")
endpoint = f"https://{foundry_name}.services.ai.azure.com/models"
datetimespace_mcp_url = os.environ["DATETIMESPACE_MCP_URL"]
customers_mcp_url = os.environ["CUSTOMERS_MCP_URL"]

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
            # "products": {
            #     # make sure you start your weather server on port 8000
            #     "url": customers_mcp_url,
            #     "transport": "sse",
            # }
        }
    )
    tools = await client.get_tools()

    print("tools: ", tools)

    # Create and run the agent
    agent = create_react_agent(llm, tools)
    agent_response = await agent.ainvoke({"messages": "What time is it here?"})
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
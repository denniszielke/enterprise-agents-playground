import asyncio
import os
import pytz
from datetime import datetime
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import (
    MagenticOneGroupChat,
)
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.teams._group_chat._magentic_one._magentic_one_orchestrator import MagenticOneOrchestrator
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

load_dotenv()

token = os.environ["GITHUB_TOKEN"]
endpoint = "https://models.inference.ai.azure.com"

o1_model_client = OpenAIChatCompletionClient(
    model="o1-mini",
    base_url=endpoint,
    api_key=token
)

reasoning_agent = AssistantAgent(name="reasoning_agent", model_client=o1_model_client, 
                            system_message=None,
                            description="A helpful assistant that can check the quality of the conversation and provide feedback to the agents. The checker agent can provide feedback on the quality of the conversation, the relevance of the responses, and the overall satisfaction of the user. The checker agent can also provide suggestions for improvement to the agents and should be consulted before completing the last task.",
                            tools=None)

# Define a tool
async def generate_code(task: str) -> str:
    print("executing code generation")

    response = await reasoning_agent.on_messages(
                    [TextMessage(content=f"Generate code for this in python: {task}", source="user")], CancellationToken()
                )
    print("done")

    return response


async def main() -> None:
    query = "Generate code to train a Regression ML model using a tabular dataset following required preprocessing steps."
    result = await generate_code(query)
    print(result.chat_message.content)

asyncio.run(main())

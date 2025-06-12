import os
import sys
import logging
from langchain_core.tools import tool
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel
from azure.ai.projects import AIProjectClient
from azure.ai.inference.tracing import AIInferenceInstrumentor
from azure.monitor.opentelemetry import configure_azure_monitor

import pytz
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

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

AIInferenceInstrumentor().instrument()

project_client = AIProjectClient(            
        credential=DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        ),
        endpoint=os.environ["PROJECT_ENDPOINT"],
    )

application_insights_connection_string = project_client.telemetry.get_connection_string()
tracing_link = f"https://ai.azure.com/tracing?wsid=/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{project_name}"

configure_azure_monitor(connection_string=application_insights_connection_string)
logger.info("Enabled telemetry logging to project, view traces at:")
logger.info(tracing_link)

@tool
def get_current_username(input: str) -> str:
    "Get the username of the current user."
    return session_name

@tool
def get_current_location(username: str) -> str:
    "Get the current timezone location of the user for a given username."
    print(username)
    if session_name in username:
        return "Europe/Berlin"
    else:
        return "America/New_York"

@tool
def get_current_time(location: str) -> str:
    "Get the current time in the given location. The pytz is used to get the timezone for that location. Location names should be in a format like America/Seattle, Asia/Bangkok, Europe/London. Anything in Germany should be Europe/Berlin"
    try:
        print("get current time for location: ", location)
        location = str.replace(location, " ", "")
        location = str.replace(location, "\"", "")
        location = str.replace(location, "\n", "")
        # Get the timezone for the city
        timezone = pytz.timezone(location)

        # Get the current time in the timezone
        now = datetime.now(timezone)
        current_time = now.strftime("%I:%M:%S %p")

        return current_time
    except Exception as e:
        print("Error: ", e)
        return "Sorry, I couldn't find the timezone for that location."
    
tools = []
# tools = [get_current_time]
tools = [get_current_username, get_current_location, get_current_time]

commandprompt = '''
    ##
    You are a helpfull assistent and should respond to user questions.
    If you cannot answer a question then say so explicitly and stop.
    
    '''

promptString = commandprompt +  """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer

Thought: you should always think about what to do

Action: the action to take, should be one of [{tool_names}]. Make sure that Actions are not commands. They should be the name of the tool to use.

Action Input: the input to the action according to the tool signature

Observation: the result of the action

... (this Thought/Action/Action Input/Observation can repeat N times)

Thought: I now know the final answer

Final Answer: the final answer to the original input question

Begin!

Question: {input}

Thought:{agent_scratchpad}

"""

from opentelemetry import trace
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span(f"{session_name}-react-tracing"):

    graph = create_react_agent(llm, tools=tools, prompt=promptString)

    input = "What is the current time here?"

    inputs = {"messages": [{"role": "user", "content": input}]}
    for chunk in graph.stream(inputs, stream_mode="updates"):
        print(chunk)
       
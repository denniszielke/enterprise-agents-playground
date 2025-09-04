import os, time
import jsonref
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import OpenApiTool, OpenApiAnonymousAuthDetails
from azure.ai.agents.models import ListSortOrder
from dotenv import load_dotenv

load_dotenv()

foundry_name = os.environ["FOUNDRY_NAME"]  # Ensure the FOUNDRY_NAME environment variable is set    
project_name = os.environ["PROJECT_NAME"]  # Ensure the PROJECT_NAME environment variable is set
model_deployment_name = os.environ["MODEL_DEPLOYMENT_NAME"]  # Ensure the MODEL_DEPLOYMENT_NAME environment variable is set
session_name = os.environ.get("SESSION_NAME", "default")
project_endpoint = os.environ["PROJECT_ENDPOINT"]

agents_client = AgentsClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential(),
)

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
project_client = AIProjectClient(            
        credential=DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        ),
        endpoint=project_endpoint,
    )

from azure.monitor.opentelemetry import configure_azure_monitor
connection_string = project_client.telemetry.get_connection_string()

configure_azure_monitor(connection_string=connection_string) #enable telemetry collection

from opentelemetry import trace
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span(f"{session_name}-code-tracing"):

    with agents_client:
        # </initialization>

        # <weather_tool_setup>
        # --- Weather OpenAPI Tool Setup ---
        # Load the OpenAPI specification for the weather service from a local JSON file using jsonref to handle references
        with open(os.path.join(os.path.dirname(__file__), "openapi_weather.json"), "r") as f:
            openapi_weather = jsonref.loads(f.read())
        # </weather_tool_setup>

        # <countries_tool_setup>
        # --- Countries OpenAPI Tool Setup ---
        # Load the OpenAPI specification for the countries service from a local JSON file
        with open(os.path.join(os.path.dirname(__file__), "openapi_currency.json"), "r") as f:
            openapi_countries = jsonref.loads(f.read())

        # Create Auth object for the OpenApiTool (note: using anonymous auth here; connection or managed identity requires additional setup)
        auth = OpenApiAnonymousAuthDetails()

        # Initialize the main OpenAPI tool definition for weather
        openapi_tool = OpenApiTool(
            name="get_weather", spec=openapi_weather, description="Retrieve weather information for a location", auth=auth
        )
        # Add the countries API definition to the same tool object
        openapi_tool.add_definition(
            name="get_countries", spec=openapi_countries, description="Retrieve a list of countries", auth=auth
        )
        # </countries_tool_setup>

        # <agent_creation>
        # --- Agent Creation ---
        # Create an agent configured with the combined OpenAPI tool definitions
        agent = agents_client.create_agent(
            model=model_deployment_name, # Specify the model deployment
            name=f"{session_name}-tools-agent", # Give the agent a name
            instructions="You are a helpful agent", # Define agent's role
            tools=openapi_tool.definitions, # Provide the list of tool definitions
        )
        print(f"Created agent, ID: {agent.id}")
        # </agent_creation>

        # <thread_management>
        # --- Thread Management ---
        # Create a new conversation thread for the interaction
        thread = agents_client.threads.create()
        print(f"Created thread, ID: {thread.id}")

        # Create the initial user message in the thread
        message = agents_client.messages.create(
            thread_id=thread.id,
            role="user",
            content="What's the weather in Seattle and What is the name and population of the country that uses currency with abbreviation THB?",
        )
        print(f"Created message, ID: {message.id}")
        # </thread_management>

        # <message_processing>
        # --- Message Processing (Run Creation and Auto-processing) ---
        # Create and automatically process the run, handling tool calls internally
        # Note: This differs from the function_tool example where tool calls are handled manually
        run = agents_client.runs.create(thread_id=thread.id, agent_id=agent.id)
        print(f"Run finished with status: {run.status}")
        # </message_processing>

        print(f"Run ID: {run.id}")
            # Poll the run as long as run status is queued or in progress
        while run.status in ["queued", "in_progress", "requires_action"]:
            # Wait for a second
            time.sleep(1)
            run = agents_client.runs.get(thread_id=thread.id, run_id=run.id)
            # [END create_run]
            print(f"Run status: {run.status}")


        # <tool_execution_loop> # Note: This section now processes completed steps, as create_and_process_run handles execution
        # --- Post-Run Step Analysis ---
        if run.status == "failed":
            print(f"Run failed: {run.last_error}")

        # Retrieve the steps taken during the run for analysis
        run_steps = project_client.agents.run_steps.list(thread_id=thread.id, run_id=run.id)
        print(run_steps)

        messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
        for msg in messages:
            if msg.text_messages:
                last_text = msg.text_messages[-1]
                print(f"{msg.role}: {last_text.text.value}")

        # <cleanup>
        # --- Cleanup ---
        # Delete the agent resource to clean up
        agents_client.delete_agent(agent.id)
        print("Deleted agent")

        # </cleanup>
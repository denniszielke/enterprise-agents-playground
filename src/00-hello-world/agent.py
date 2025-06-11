
# Import necessary libraries and modules
import sys
import logging
import os, time
from azure.ai.agents import AgentsClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder

from dotenv import load_dotenv

load_dotenv()

# Retrieve endpoint and model deployment name from environment variables

foundry_name = os.environ["FOUNDRY_NAME"]  # Ensure the FOUNDRY_NAME environment variable is set    
project_name = os.environ["PROJECT_NAME"]  # Ensure the PROJECT_NAME environment variable is set
model_deployment_name = os.environ["MODEL_DEPLOYMENT_NAME"]  # Ensure the MODEL_DEPLOYMENT_NAME environment variable is set
session_name = os.environ.get("SESSION_NAME", "default")

project_endpoint = f"https://{foundry_name}.services.ai.azure.com/api/projects/{project_name}"

# [START create_agents_client]
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
        endpoint=os.environ["PROJECT_ENDPOINT"],
    )

from azure.monitor.opentelemetry import configure_azure_monitor
connection_string = project_client.telemetry.get_connection_string()

if not connection_string:
    print("Application Insights is not enabled. Enable by going to Tracing in your Azure AI Foundry project.")
    exit()


tracing_link = f"https://ai.azure.com/tracing?wsid=/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{project_name}"
print(f"View traces at: {tracing_link}")

configure_azure_monitor(connection_string=connection_string) #enable telemetry collection

from opentelemetry import trace
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span(f"{session_name}-tracing"):
    with agents_client:

        # [START create_agent]

        agent = agents_client.create_agent(
            model=model_deployment_name,
            name=f"{session_name}-agent",
            instructions="You are helpful agent",
        )
        # [END create_agent]
        print(f"Created agent, agent ID: {agent.id}")

        # [START create_thread]
        thread = agents_client.threads.create()
        # [END create_thread]
        print(f"Created thread, thread ID: {thread.id}")

        # List all threads for the agent
        # [START list_threads]
        threads = agents_client.threads.list()
        # [END list_threads]

        # [START create_message]
        message = agents_client.messages.create(thread_id=thread.id, role="user", content="Hello, tell me a joke")
        # [END create_message]
        print(f"Created message, message ID: {message.id}")

        # [START create_run]
        run = agents_client.runs.create(thread_id=thread.id, agent_id=agent.id)

        # Poll the run as long as run status is queued or in progress
        while run.status in ["queued", "in_progress", "requires_action"]:
            # Wait for a second
            time.sleep(1)
            run = agents_client.runs.get(thread_id=thread.id, run_id=run.id)
            # [END create_run]
            print(f"Run status: {run.status}")

        if run.status == "failed":
            print(f"Run error: {run.last_error}")

        agents_client.delete_agent(agent.id)
        print("Deleted agent")

        # [START list_messages]
        messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
        for msg in messages:
            if msg.text_messages:
                last_text = msg.text_messages[-1]
                print(f"{msg.role}: {last_text.text.value}")
        # [END list_messages]
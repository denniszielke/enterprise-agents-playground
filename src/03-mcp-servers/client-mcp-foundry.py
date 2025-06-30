import os, time
import json
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import MessageTextContent, ListSortOrder
from azure.identity import DefaultAzureCredential
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.agents.models import ListSortOrder
load_dotenv()

foundry_name = os.environ["FOUNDRY_NAME"]  # Ensure the FOUNDRY_NAME environment variable is set    
project_name = os.environ["PROJECT_NAME"]  # Ensure the PROJECT_NAME environment variable is set
model_deployment_name = os.environ["MODEL_DEPLOYMENT_NAME"]  # Ensure the MODEL_DEPLOYMENT_NAME environment variable is set
session_name = os.environ.get("SESSION_NAME", "default")
project_endpoint = os.environ["PROJECT_ENDPOINT"]
datetimespace_mcp_url = os.environ["DATETIMESPACE_MCP_URL"]
customers_mcp_url = os.environ["CUSTOMERS_MCP_URL"]

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
project_client = AIProjectClient(            
        credential=DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        ),
        endpoint=project_endpoint,
        api_version="2025-05-15-preview"
    )


with project_client:

        # Create agent with code interpreter tool and tools_resources
    agent = project_client.agents.create_agent(
        model=model_deployment_name,
        name=f"{session_name}-mcp-agent",
        instructions="You are helpful agent. Only use the mcp tools you can use to answer the question. If you do not how to to answer a questions with the tools available, then say so and stop processing.",
        tools= [
            {
                "type": "mcp",
                "server_label": "customer_mcp_server",
                "server_url": datetimespace_mcp_url,
                "require_approval": "never"
            }
        ],
        tool_resources=None
    )

    print(f"Created agent, agent ID: {agent.id}")

    thread = project_client.agents.threads.create()
    print(f"Created thread, thread ID: {thread.id}")

    message = project_client.agents.messages.create(
        thread_id=thread.id, role="user", content="check the current time",
    )
    print(f"Created message, message ID: {message.id}")

    run = project_client.agents.runs.create(thread_id=thread.id, agent_id=agent.id)


    # Poll the run as long as run status is queued or in progress
    while run.status in ["queued", "in_progress", "requires_action"]:
        # Wait for a second
        time.sleep(1)
        run = project_client.agents.runs.get(thread_id=thread.id, run_id=run.id)
        print(f"Run status: {run.status}")

    if run.status == "failed":
        print(f"Run error: {run.last_error}")

    run_steps = list(project_client.agents.run_steps.list(thread_id=thread.id, run_id=run.id))
    for step in run_steps:
        print(f"Run step: {step.id}, status: {step.status}, type: {step.type}")

        if step.type == "tool_calls":
            print("Tool call details:")
            print("step_details:", step.step_details)
            # Check if tool_calls exists
            tool_calls = getattr(step.step_details, "tool_calls", None)
            if tool_calls is not None:
                for tool_call in tool_calls:
                    print(tool_call)
                    # print(json.dumps(tool_call.as_dict(), indent=2))
            else:
                print("No tool_calls found in step_details.")

    messages = project_client.agents.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
    for data_point in messages:
        last_message_content = data_point.content[-1]
        if isinstance(last_message_content, MessageTextContent):
            print(f"{data_point.role}: {last_message_content.text.value}")

    # project_client.agents.delete_agent(agent.id)
    # print(f"Deleted agent, agent ID: {agent.id}")
import os, time
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import BingGroundingTool
from azure.ai.agents.models import MessageRole
from azure.identity import DefaultAzureCredential
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.agents.models import ListSortOrder
from azure.ai.projects import AIProjectClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

foundry_name = os.environ["FOUNDRY_NAME"]  # Ensure the FOUNDRY_NAME environment variable is set    
project_name = os.environ["PROJECT_NAME"]  # Ensure the PROJECT_NAME environment variable is set
model_deployment_name = os.environ["MODEL_DEPLOYMENT_NAME"]  # Ensure the MODEL_DEPLOYMENT_NAME environment variable is set
session_name = os.environ.get("SESSION_NAME", "default")
project_endpoint = os.environ["PROJECT_ENDPOINT"]
bing_connection_id = os.environ["BING_CONNECTION_NAME"]  # Ensure the BING_CONNECTION_NAME environment variable is set

agents_client = AgentsClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential()
)

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

with tracer.start_as_current_span(f"{session_name}-bing-grounding-tracing"):

    with agents_client:

        # Initialize the Bing Grounding tool
        # [START create_bing_grounding_tool]
        bing_tool = BingGroundingTool(connection_id=bing_connection_id)
        print(f"Connected Bing Grounding tool with connection ID: {bing_connection_id}")
        # [END create_bing_grounding_tool]

        # Create agent with Bing grounding tool
        # [START create_agent_with_bing_grounding]
        agent = agents_client.create_agent(
            model=model_deployment_name,
            name=f"{session_name}-bing-grounding-agent",
            instructions="You are a helpful agent that can search the internet for current information using Bing. Always provide accurate, up-to-date information and cite your sources when possible.",
            tools=bing_tool.definitions,
        )
        print(f"Created agent, agent ID: {agent.id}")
        # [END create_agent_with_bing_grounding]

        # [START create_thread]
        thread = agents_client.threads.create()
        # [END create_thread]
        print(f"Created thread, thread ID: {thread.id}")

        # List all threads for the agent
        # [START list_threads]
        threads = agents_client.threads.list()
        # [END list_threads]

        # Create a message asking for current information that requires web search
        # [START create_message]
        message = agents_client.messages.create(
            thread_id=thread.id,
            role="user",
            content="What are the latest developments in artificial intelligence and machine learning announced this week? Please provide specific examples and sources.",
        )
        print(f"Created message, message ID: {message.id}")
        # [END create_message]

        # [START create_run]
        run = agents_client.runs.create(thread_id=thread.id, agent_id=agent.id)
        print(f"Created run, run ID: {run.id}")

        # Poll the run as long as run status is queued or in progress
        while run.status in ["queued", "in_progress", "requires_action"]:
            # Wait for a second
            time.sleep(1)
            run = agents_client.runs.get(thread_id=thread.id, run_id=run.id)
            print(f"Run status: {run.status}")

        if run.status == "failed":
            print(f"Run error: {run.last_error}")
        # [END create_run]

        # [START get_messages]
        messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
        for msg in messages:
            if msg.text_messages:
                last_text = msg.text_messages[-1]
                print(f"\n{msg.role}: {last_text.text.value}")
                for annotation in last_text.text.annotations:
                    print(f"Annotation: {annotation.text} = {annotation.url_citation.title}")
                    print(f"URL: {annotation.url_citation.url}")
        # [END get_messages]

        # [START get_run_steps]
        # Optionally output the run steps used by the agent
        run_steps = agents_client.run_steps.list(thread_id=thread.id, run_id=run.id)
        print(f"\n--- Run Steps Details ---")
        for step in run_steps:
            print(f"Step {step.id} status: {step.status}")
            
            # Check if there are tool calls in the step details
            if hasattr(step, 'step_details') and hasattr(step.step_details, 'tool_calls'):
                tool_calls = step.step_details.tool_calls
                if tool_calls:
                    print("  Tool calls:")
                    for call in tool_calls:
                        print(f"    Tool Call ID: {call.id}")
                        print(f"    Type: {call.type}")
                        
                        if hasattr(call, 'bing_grounding') and call.bing_grounding:
                            print(f"    Bing Grounding Request URL: {call.bing_grounding.get('requesturl', 'N/A')}")
                            print(f"    Bing Grounding Response Metadata: {call.bing_grounding.get('response_metadata', 'N/A')}")
            print()  # add an extra newline between steps
        # [END get_run_steps]

        # Test with another query about current events
        # [START second_query]
        print(f"\n--- Second Query ---")
        message2 = agents_client.messages.create(
            thread_id=thread.id,
            role="user",
            content="What is the current weather in Seattle, WA and what are the top technology companies hiring there right now?",
        )
        print(f"Created second message, message ID: {message2.id}")

        run2 = agents_client.runs.create(thread_id=thread.id, agent_id=agent.id)
        print(f"Created second run, run ID: {run2.id}")

        # Poll the second run
        while run2.status in ["queued", "in_progress", "requires_action"]:
            time.sleep(1)
            run2 = agents_client.runs.get(thread_id=thread.id, run_id=run2.id)
            print(f"Second run status: {run2.status}")

        if run2.status == "failed":
            print(f"Second run error: {run2.last_error}")

        # Get all messages including the new response
        messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
        print(f"\n--- All Messages ---")
        for msg in messages:
            if msg.text_messages:
                last_text = msg.text_messages[-1]
                print(f"\n{msg.role}: {last_text.text.value}")
        # [END second_query]

        # [START cleanup]
        # Delete the agent when done
        agents_client.delete_agent(agent.id)
        print("\nDeleted agent")
        # [END cleanup]

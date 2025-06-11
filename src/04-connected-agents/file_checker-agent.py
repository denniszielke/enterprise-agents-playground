import os, time
import requests
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import CodeInterpreterTool
from azure.ai.agents.models import FilePurpose, MessageRole
from azure.identity import DefaultAzureCredential
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from azure.ai.agents.models import ListSortOrder
from azure.ai.agents.models import (
    MessageTextContent,
    MessageInputContentBlock,
    MessageImageUrlParam,
    MessageInputTextBlock,
    MessageInputImageUrlBlock,
)
from azure.ai.agents.models import ConnectedAgentTool, MessageRole

load_dotenv()

foundry_name = os.environ["FOUNDRY_NAME"]  # Ensure the FOUNDRY_NAME environment variable is set    
project_name = os.environ["PROJECT_NAME"]  # Ensure the PROJECT_NAME environment variable is set
model_deployment_name = "gpt-4o"  # Ensure the MODEL_DEPLOYMENT_NAME environment variable is set
session_name = os.environ.get("SESSION_NAME", "default")

invoice_url = "https://likvi.de/assets/img/blog/rechnungsvorlage.jpg"

invoice_agent_name = f"{session_name}-invoice-agent"
invoice_agent_id = ""
invoice_agent_description = ""

agents_client = AgentsClient(
    endpoint=os.environ["PROJECT_ENDPOINT"],
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

with agents_client:

    system_prompt = """
Look at the image attached and extract all details as best as suitable for the file type."""

    # Create agent with code interpreter tool and tools_resources
    agents = project_client.agents.list_agents(limit=2)
     # Iterate items by page. Each page will be limited by two items.
    for i, page in enumerate(agents.by_page()):
        print(f"Items on page {i}")
        for one_agent in page:
            if (one_agent.name == invoice_agent_name):
                print(f"Found agent {one_agent.name} with ID {one_agent.id}")
                invoice_agent_id = one_agent.id
                invoice_agent_description = one_agent.description
                print (f"Agent description: {invoice_agent_description}")
                print (f"Agent ID: {invoice_agent_id}")
                print (f"Agent name: {invoice_agent_name}")
                break
            print(one_agent.id)

    if (not invoice_agent_id or not invoice_agent_description):
        print("invoice agent was not found")
        exit()

    invoice_agent_name = invoice_agent_name.replace("-", "_")

    connected_agent = ConnectedAgentTool(
        id=invoice_agent_id, name=invoice_agent_name, description=invoice_agent_description
    )

    agent = agents_client.create_agent(
        model=model_deployment_name,
        name=f"{session_name}-checker-agent",
        instructions=system_prompt,
        tools=[
            connected_agent.definitions[0],
        ],
    )

    input_message = "Hello, check this image"
    url_param = MessageImageUrlParam(url=invoice_url, detail="high")
    content_blocks: List[MessageInputContentBlock] = [
        MessageInputTextBlock(text=input_message),
        MessageInputImageUrlBlock(image_url=url_param),
    ]

    # [START create_thread]
    thread = agents_client.threads.create()
    # [END create_thread]
    print(f"Created thread, thread ID: {thread.id}")

    # List all threads for the agent
    # [START list_threads]
    threads = agents_client.threads.list()
    # [END list_threads]

    # Create a message
    message = agents_client.messages.create(
        thread_id=thread.id,
        role="user",
        content=content_blocks,
    )
    print(f"Created message, message ID: {message.id}")

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

        # [START get_messages_and_save_files]
    messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
    for msg in messages:
        if msg.text_messages:
            last_text = msg.text_messages[-1]
            print(f"{msg.role}: {last_text.text.value}")

        # for image_content in msg.image_contents:
        #     file_id = image_content.image_file.file_id
        #     print(f"Image File ID: {file_id}")
        #     file_name = f"{file_id}_image_file.png"
        #     project_client.agents.files.save(file_id=file_id, file_name=file_name)
        #     print(f"Saved image file to: {Path.cwd() / file_name}")

        for file_path_annotation in msg.file_path_annotations:
            print(f"File Paths:")
            print(f"Type: {file_path_annotation.type}")
            print(f"Text: {file_path_annotation.text}")
            print(f"File ID: {file_path_annotation.file_path.file_id}")
            print(f"Start Index: {file_path_annotation.start_index}")
            print(f"End Index: {file_path_annotation.end_index}")
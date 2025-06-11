import os, time
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import CodeInterpreterTool
from azure.ai.agents.models import FilePurpose, MessageRole
from azure.identity import DefaultAzureCredential
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.agents.models import ListSortOrder
load_dotenv()

foundry_name = os.environ["FOUNDRY_NAME"]  # Ensure the FOUNDRY_NAME environment variable is set    
project_name = os.environ["PROJECT_NAME"]  # Ensure the PROJECT_NAME environment variable is set
model_deployment_name = os.environ["MODEL_DEPLOYMENT_NAME"]  # Ensure the MODEL_DEPLOYMENT_NAME environment variable is set
session_name = os.environ.get("SESSION_NAME", "default")

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

    # Upload a file and wait for it to be processed
    # [START upload_file_and_create_agent_with_code_interpreter]
    file = project_client.agents.files.upload_and_poll(file_path="./quarterly_results.csv", purpose=FilePurpose.AGENTS)
    print(f"Uploaded file, file ID: {file.id}")

    code_interpreter = CodeInterpreterTool(file_ids=[file.id])

    # Create agent with code interpreter tool and tools_resources
    agent = agents_client.create_agent(
        model=model_deployment_name,
        name=f"{session_name}-agent",
        instructions="You are helpful agent",
        tools=code_interpreter.definitions,
        tool_resources=code_interpreter.resources,
    )
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
        content="Could you please create bar chart in TRANSPORTATION sector for the operating profit from the uploaded csv file and provide file to me?",
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

    project_client.agents.files.delete(file_id=file.id)
    print("Deleted file")

    # [START get_messages_and_save_files]
    messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
    for msg in messages:
        if msg.text_messages:
            last_text = msg.text_messages[-1]
            print(f"{msg.role}: {last_text.text.value}")

        for image_content in msg.image_contents:
            file_id = image_content.image_file.file_id
            print(f"Image File ID: {file_id}")
            file_name = f"{file_id}_image_file.png"
            project_client.agents.files.save(file_id=file_id, file_name=file_name)
            print(f"Saved image file to: {Path.cwd() / file_name}")

        for file_path_annotation in msg.file_path_annotations:
            print(f"File Paths:")
            print(f"Type: {file_path_annotation.type}")
            print(f"Text: {file_path_annotation.text}")
            print(f"File ID: {file_path_annotation.file_path.file_id}")
            print(f"Start Index: {file_path_annotation.start_index}")
            print(f"End Index: {file_path_annotation.end_index}")
    # [END get_messages_and_save_files]

    agents_client.delete_agent(agent.id)
    print("Deleted agent")
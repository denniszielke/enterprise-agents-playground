import os, time
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import (
    FileSearchTool,
    FilePurpose,
    ListSortOrder
)
from azure.identity import DefaultAzureCredential
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

model_deployment_name = os.environ["MODEL_DEPLOYMENT_NAME"]  # Ensure the MODEL_DEPLOYMENT_NAME environment variable is set
session_name = os.environ.get("SESSION_NAME", "default")

agents_client = AgentsClient(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)

with agents_client:

    # Upload file and create vector store
    # [START upload_file_create_vector_store_and_agent_with_file_search_tool]
    file = agents_client.files.upload_and_poll(file_path="./product_info_1.md", purpose=FilePurpose.AGENTS)
    print(f"Uploaded file, file ID: {file.id}")

    vector_store = agents_client.vector_stores.create_and_poll(file_ids=[file.id], name="my_vectorstore")
    print(f"Created vector store, vector store ID: {vector_store.id}")

    # Create file search tool with resources followed by creating agent
    file_search = FileSearchTool(vector_store_ids=[vector_store.id])

    agent = agents_client.create_agent(
        model=model_deployment_name,
        name=f"{session_name}-agent",
        instructions="Hello, you are helpful agent and can search information from uploaded files",
        tools=file_search.definitions,
        tool_resources=file_search.resources,
    )
    # [END upload_file_create_vector_store_and_agent_with_file_search_tool]

    print(f"Created agent, ID: {agent.id}")

    # Create thread for communication
    # [START create_thread]
    thread = agents_client.threads.create()
    # [END create_thread]
    print(f"Created thread, ID: {thread.id}")

    # List all threads for the agent
    # [START list_threads]
    threads = agents_client.threads.list()
    # [END list_threads]

    # Create message to thread
    # [START create_message]
    message = agents_client.messages.create(
        thread_id=thread.id, role="user", content="Hello, can you tell me about TrailMaster X4 Tent?"
    )
    # [END create_message]
    print(f"Created message, ID: {message.id}")

    # Create and process agent run in thread with tools
    # [START create_run]
    run = agents_client.runs.create(thread_id=thread.id, agent_id=agent.id)
    
    # Poll the run as long as run status is queued or in progress
    while run.status in ["queued", "in_progress", "requires_action"]:
        # Wait for a second
        time.sleep(1)
        run = agents_client.runs.get(thread_id=thread.id, run_id=run.id)
        print(f"Run status: {run.status}")
    # [END create_run]
    
    print(f"Run finished with status: {run.status}")

    if run.status == "failed":
        # Check if you got "Rate limit is exceeded.", then you want to get more quota
        print(f"Run failed: {run.last_error}")

    # [START teardown]
    # Delete the file when done
    agents_client.vector_stores.delete(vector_store.id)
    print("Deleted vector store")

    agents_client.files.delete(file_id=file.id)
    print("Deleted file")

    # Delete the agent when done
    agents_client.delete_agent(agent.id)
    print("Deleted agent")
    # [END teardown]

    # Fetch and log all messages
    # [START get_messages]
    messages = agents_client.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
    for msg in messages:
        if msg.text_messages:
            last_text = msg.text_messages[-1]
            print(f"{msg.role}: {last_text.text.value}")
            
        for file_path_annotation in msg.file_path_annotations:
            print(f"File Paths:")
            print(f"Type: {file_path_annotation.type}")
            print(f"Text: {file_path_annotation.text}")
            print(f"File ID: {file_path_annotation.file_path.file_id}")
            print(f"Start Index: {file_path_annotation.start_index}")
            print(f"End Index: {file_path_annotation.end_index}")
    # [END get_messages]
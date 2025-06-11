import os, time
import requests
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
model_deployment_name = "gpt-4o"  # Ensure the MODEL_DEPLOYMENT_NAME environment variable is set
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
    invoice_template_file = project_client.agents.files.upload_and_poll(file_path="./invoice_template.xml", purpose=FilePurpose.AGENTS)
    print(f"Uploaded file, file ID: {invoice_template_file.id}")

    invoice_explaination_file = project_client.agents.files.upload_and_poll(file_path="./invoice_explaination.txt", purpose=FilePurpose.AGENTS)
    print(f"Uploaded file, file ID: {invoice_explaination_file.id}")

    code_interpreter = CodeInterpreterTool(file_ids=[invoice_template_file.id, invoice_explaination_file.id])

    system_prompt = """
Look at the image attached as input to extract all the invoice information you can find. I want to you extract all the relevant information you can from the image and create a XRechnung Beispiel XML filled with all known values. Replace all existing sample values with either the extracted details from the image or set them to empty."""

    # Create agent with code interpreter tool and tools_resources
    agent = agents_client.create_agent(
        model=model_deployment_name,
        name=f"{session_name}-invoice-agent",
        description="Agent to parse invoice image files and create XRechnung XML",
        instructions=system_prompt,
        tools=code_interpreter.definitions,
        tool_resources=code_interpreter.resources,
    )
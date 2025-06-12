import os
import json
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from dotenv import load_dotenv

load_dotenv()

foundry_name = os.environ["FOUNDRY_NAME"]  # Ensure the FOUNDRY_NAME environment variable is set    
project_name = os.environ["PROJECT_NAME"]  # Ensure the PROJECT_NAME environment variable is set
model_deployment_name = os.environ["MODEL_DEPLOYMENT_NAME"]  # Ensure the MODEL_DEPLOYMENT_NAME environment variable is set
session_name = os.environ.get("SESSION_NAME", "default")
project_endpoint = os.environ["PROJECT_ENDPOINT"]

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
project_client = AIProjectClient(            
        credential=DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True
        ),
        endpoint=project_endpoint,
    )

from azure.ai.evaluation import AIAgentConverter

# Initialize the converter that will be backed by the project.
converter = AIAgentConverter(project_client)

thread_id = "thread_DlcDXX2Ovf9qFOFUV5dCUhyS"  # Replace with your actual thread ID
run_id = "run_wLT8SkjzO1jt8KUjq3OGFf8l"
file_name = "evaluation_data.jsonl"

# Get a single agent run data
evaluation_data_single_run = converter.convert(thread_id=thread_id, run_id=run_id)

# Run this to save thread data to a JSONL file for evaluation
# Save the agent thread data to a JSONL file
evaluation_data = converter.prepare_evaluation_data(thread_ids=thread_id, filename="evaluation_data.jsonl")
print(json.dumps(evaluation_data, indent=4))

from azure.ai.evaluation import (
    ToolCallAccuracyEvaluator,
    AzureOpenAIModelConfiguration,
    IntentResolutionEvaluator,
    TaskAdherenceEvaluator,
)
from pprint import pprint

model_config = AzureOpenAIModelConfiguration(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    azure_deployment=os.environ["MODEL_DEPLOYMENT_NAME"],
)
# Needed to use content safety evaluators
azure_ai_project = {
    "subscription_id": os.environ["SUBSCRIPTION_ID"],
    "project_name": os.environ["PROJECT_NAME"],
    "resource_group_name": os.environ["RESOURCE_GROUP"],
}

intent_resolution = IntentResolutionEvaluator(model_config=model_config)

tool_call_accuracy = ToolCallAccuracyEvaluator(model_config=model_config)

task_adherence = TaskAdherenceEvaluator(model_config=model_config)

from azure.ai.evaluation import evaluate

response = evaluate(
    data=file_name,
    evaluators={
        "tool_call_accuracy": tool_call_accuracy,
        "intent_resolution": intent_resolution,
        "task_adherence": task_adherence,
    },
    azure_ai_project={
        "subscription_id": os.environ["SUBSCRIPTION_ID"],
        "project_name": os.environ["PROJECT_NAME"],
        "resource_group_name": os.environ["RESOURCE_GROUP"],
    },
)
pprint(f'AI Foundary URL: {response.get("studio_url")}')

# alternatively, you can use the following to get the evaluation results in memory

# average scores across all runs
pprint(response["metrics"])
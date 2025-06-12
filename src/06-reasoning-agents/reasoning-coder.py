import os
import asyncio
from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential

from semantic_kernel.agents import AzureAIAgent, AzureAIAgentThread
from semantic_kernel.functions import kernel_function

# https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-types/azure-ai-agent?pivots=programming-language-python

# Load environment variables
load_dotenv(override=True)

# Retrieve endpoint and model deployment name from environment variables

foundry_name = os.environ["FOUNDRY_NAME"]  # Ensure the FOUNDRY_NAME environment variable is set    
project_name = os.environ["PROJECT_NAME"]  # Ensure the PROJECT_NAME environment variable is set
model_deployment_name = os.environ["REASONING_MODEL_DEPLOYMENT_NAME"] # os.environ["MODEL_DEPLOYMENT_NAME"])  # Ensure the MODEL_DEPLOYMENT_NAME environment variable is set
session_name = os.environ.get("SESSION_NAME", "default")

project_endpoint = os.environ.get("PROJECT_ENDPOINT", f"https://{foundry_name}.services.ai.azure.com/api/projects/{project_name}")

# Create a class for our code generation plugin
class CodeGenerationPlugin:
    """A plugin to generate code based on a description"""
    
    @kernel_function(description="Generates Python code based on a task description")
    def generate_python_code(self, task_description: str) -> str:
        """
        Generates Python code based on the given task description
        
        Args:
            task_description: A description of what the code should do
            
        Returns:
            The generated Python code as a string
        """
        # This function will be handled by the AI model
        # The agent will recognize this as a function to generate code
        return f"Generated code for: {task_description}"

async def main() -> None:
    """Main function that handles the entire workflow within the async with block"""
    
    # Define the query
    query = "Generate code to train a Regression ML model using a tabular dataset following required preprocessing steps."
    
    # Keep everything within the async with block to ensure the client remains active
    async with (
        DefaultAzureCredential() as creds,
        AzureAIAgent.create_client(credential=creds, endpoint=project_endpoint) as client
    ):
        try:
            # Create agent on the Azure AI agent service
            print("Creating agent...")
            agent_definition = await client.agents.create_agent(
                model=model_deployment_name,
                name=f"{session_name}_code_agent",
                instructions="""You are a helpful assistant that can generate high-quality Python code based on requirements.
                When generating code, ensure it is clear, well-structured, and includes appropriate comments.
                Always consider best practices, error handling, and code readability."""
            )

            # Set temperature and top_p to None for o1, o3 or o4 models or the mini models
            if model_deployment_name in ["o1", "o3", "o4", "o1-mini", "o3-mini", "o4-mini"]:
                agent_definition.temperature = None  # Set temperature to None
                agent_definition.top_p = None  # Set top_p to None

            # Create a Semantic Kernel agent based on the agent definition
            agent = AzureAIAgent(
                client=client,
                definition=agent_definition,
                plugins=[CodeGenerationPlugin()]  # Add our code generation plugin
            )
            
            # Create a thread for the agent
            thread = AzureAIAgentThread(client=client)
            
            try:
                # Execute code generation
                print("Executing code generation")
                response = await agent.get_response(
                    messages=f"Generate code for this in python: {query}", 
                    thread=thread
                )
                
                # Print the result
                print("Code generation complete:")
                print(response.content)
                
            finally:
                # Clean up thread
                if thread:
                    print("Cleaning up thread...")
                    await thread.delete()
        finally:
            # Clean up agent
            if 'agent' in locals() and agent and agent.id:
                print("Cleaning up agent...")
                await client.agents.delete_agent(agent.id)

if __name__ == "__main__":
    asyncio.run(main())

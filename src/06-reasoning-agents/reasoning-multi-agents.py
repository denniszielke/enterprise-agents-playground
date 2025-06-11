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
model_deployment_name = os.environ["MODEL_DEPLOYMENT_NAME"]  # Ensure the MODEL_DEPLOYMENT_NAME environment variable is set
reasoning_model_deployment_name = os.environ.get("REASONING_MODEL_DEPLOYMENT_NAME", model_deployment_name)  # Use reasoning model if specified
session_name = os.environ.get("SESSION_NAME", "default")

project_endpoint = os.environ.get("PROJECT_ENDPOINT", f"https://{foundry_name}.services.ai.azure.com/api/projects/{project_name}")

# Create plugin classes for our specialized agents
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
        return f"Generated code for: {task_description}"

class CodeReviewPlugin:
    """A plugin to review code following best practices"""
    
    @kernel_function(description="Reviews Python code and provides feedback")
    def review_code(self, code: str) -> str:
        """
        Reviews Python code and provides feedback based on best practices
        
        Args:
            code: The Python code to review
            
        Returns:
            Feedback on the code as a string
        """
        # This function will be handled by the AI model
        return f"Review feedback for the code"

class CodeImprovementPlugin:
    """A plugin to improve code based on review feedback"""
    
    @kernel_function(description="Improves Python code based on review feedback")
    def improve_code(self, code: str, feedback: str) -> str:
        """
        Improves Python code based on review feedback
        
        Args:
            code: The original Python code
            feedback: Feedback from the code review
            
        Returns:
            Improved Python code as a string
        """
        # This function will be handled by the AI model
        return f"Improved code based on feedback"

class CodeEvaluationPlugin:
    """A plugin to evaluate and compare code versions"""
    
    @kernel_function(description="Evaluates and compares code versions")
    def evaluate_code(self, original_code: str, improved_code: str) -> str:
        """
        Evaluates and compares original and improved code versions
        
        Args:
            original_code: The original Python code
            improved_code: The improved Python code
            
        Returns:
            Evaluation and comparison of both code versions
        """
        # This function will be handled by the AI model
        return f"Evaluation of original vs. improved code"

async def create_agent(client, role, instructions, custom_model_deployment_name=None, plugins=None):
    """Helper function to create an agent with specific role and instructions"""
    print(f"Creating {role} agent...")
    
    agent_definition = await client.agents.create_agent(
        model=custom_model_deployment_name or model_deployment_name,
        name=f"{session_name}_{role}_agent",
        instructions=instructions
    )
    
    # Set temperature and top_p to None for o1, o3, o4 models or mini models
    if model_deployment_name or custom_model_deployment_name in ["o1", "o3", "o4", "o1-mini", "o3-mini", "o4-mini"]:
        agent_definition.temperature = None
        agent_definition.top_p = None
    
    # Create and return the agent
    return AzureAIAgent(
        client=client,
        definition=agent_definition,
        plugins=plugins or []
    )

async def execute_agent(agent, prompt, thread):
    """Helper function to execute an agent with a prompt on a thread"""
    print(f"Executing {agent.definition.name}...")
    response = await agent.get_response(
        messages=prompt,
        thread=thread
    )
    return response.content

async def main() -> None:
    """Main function that handles the entire workflow with multiple specialized agents"""
    
    # Define the query
    query = "Generate code to train a Regression ML model using a tabular dataset following required preprocessing steps."
    
    # Keep everything within the async with block to ensure the client remains active
    async with (
        DefaultAzureCredential() as creds,
        AzureAIAgent.create_client(credential=creds, endpoint=project_endpoint) as client
    ):
        try:
            # Create thread for communication between agents
            thread = AzureAIAgentThread(client=client)
            
            # Create specialized agents
            coder_agent = await create_agent(
                client,
                "coder",
                """You are an expert Python coder specialized in machine learning.
                When generating code, ensure it is clear, well-structured, and includes appropriate comments.
                Always consider best practices, error handling, and code readability.""",
                custom_model_deployment_name=model_deployment_name,
                plugins=[CodeGenerationPlugin()]
            )
            
            reviewer_agent = await create_agent(
                client,
                "reviewer",
                """You are a code reviewer specialized in Python and machine learning code.
                Review the given code following PEP8 guidelines and identify potential bugs or improvements.
                Provide specific, actionable feedback as a bullet list.""",
                custom_model_deployment_name=reasoning_model_deployment_name,
                plugins=[CodeReviewPlugin()]
            )
            
            improver_agent = await create_agent(
                client,
                "improver",
                """You are a code improver specialized in Python and machine learning.
                Improve the given code based on feedback provided by code reviews.
                Focus on implementation, optimization, and best practices.""",
                custom_model_deployment_name=model_deployment_name,
                plugins=[CodeImprovementPlugin()]
            )
            
            evaluator_agent = await create_agent(
                client,
                "evaluator",
                """You are a code evaluator specialized in comparing and rating Python code quality.
                Compare original and improved code, providing insights on improvements and rating both versions.
                Focus on readability, efficiency, maintainability, and adherence to best practices.""",
                custom_model_deployment_name=model_deployment_name,
                plugins=[CodeEvaluationPlugin()]
            )
            
            try:
                # Step 1: Generate initial code
                print("\n===== STEP 1: GENERATE INITIAL CODE =====")
                initial_code = await execute_agent(
                    coder_agent,
                    f"Generate Python code for this task: {query}",
                    thread
                )
                print("\nInitial code generated:")
                print(initial_code)
                
                # Maximum number of improvement iterations
                max_iterations = 2
                current_code = initial_code
                
                for i in range(max_iterations):
                    # Step 2: Review code
                    print(f"\n===== STEP 2.{i+1}: REVIEW CODE =====")
                    review_feedback = await execute_agent(
                        reviewer_agent,
                        f"Review this Python code following PEP8 guidelines and identify potential bugs or improvements:\n\n{current_code}",
                        thread
                    )
                    print("\nReview feedback:")
                    print(review_feedback)
                    
                    # Step 3: Improve code based on feedback
                    print(f"\n===== STEP 3.{i+1}: IMPROVE CODE =====")
                    improved_code = await execute_agent(
                        improver_agent,
                        f"Improve this Python code based on the review feedback:\n\nCODE:\n{current_code}\n\nFEEDBACK:\n{review_feedback}",
                        thread
                    )
                    print("\nImproved code:")
                    print(improved_code)
                    
                    # Update current code for next iteration
                    current_code = improved_code
                    
                    # Check if code has addressed major issues (simplified approach)
                    # In a real system, you might want a more sophisticated way to determine when to stop iterating
                    if "All issues have been addressed" in review_feedback or "No issues found" in review_feedback:
                        print("\nAll major issues have been addressed. Stopping improvement cycle.")
                        break
                
                # Step 4: Final evaluation
                print("\n===== STEP 4: FINAL EVALUATION =====")
                evaluation = await execute_agent(
                    evaluator_agent,
                    f"Compare and evaluate these two versions of Python code:\n\nORIGINAL CODE:\n{initial_code}\n\nIMPROVED CODE:\n{current_code}",
                    thread
                )
                print("\nFinal evaluation:")
                print(evaluation)
                
                # Return the final improved code
                print("\n===== FINAL IMPROVED CODE =====")
                print(current_code)
                
            finally:
                # Clean up thread
                if thread:
                    print("Cleaning up thread...")
                    await thread.delete()
                    
                # Clean up agents
                for agent in [coder_agent, reviewer_agent, improver_agent, evaluator_agent]:
                    if agent and agent.id:
                        print(f"Cleaning up agent {agent.definition.name}...")
                        await client.agents.delete_agent(agent.id)
        except Exception as e:
            print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())

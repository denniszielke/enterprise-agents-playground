import os
import sys
import logging
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.messages import BaseMessage, SystemMessage
from langchain import agents
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.tools import tool
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

load_dotenv()

llm: AzureAIChatCompletionsModel = None

foundry_name = os.environ["FOUNDRY_NAME"]  # Ensure the FOUNDRY_NAME environment variable is set    
project_name = os.environ["PROJECT_NAME"]  # Ensure the PROJECT_NAME environment variable is set
model_deployment_name = os.environ["MODEL_DEPLOYMENT_NAME"]  # Ensure the MODEL_DEPLOYMENT_NAME environment variable is set
session_name = os.environ.get("SESSION_NAME", "default")
subscription_id = os.environ["SUBSCRIPTION_ID"]  # Ensure the SUBSCRIPTION_ID environment variable is set
resource_group = os.environ["RESOURCE_GROUP"]  # Ensure the RESOURCE_GROUP environment variable is set
endpoint = f"https://{foundry_name}.services.ai.azure.com/models"

credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)

model_deployment_name = "gpt-4o"
token_provider = get_bearer_token_provider(
    credential, "https://ai.azure.com/.default"
)

model = AzureAIChatCompletionsModel(
    azure_ad_token_provider=token_provider,
    endpoint=endpoint,
    model=model_deployment_name,
    temperature=0, 
    openai_api_type="azure_ad",
    credential=credential,
    client_kwargs={"logging_enable": True, "credential_scopes": [ "https://ai.azure.com/.default"]},
)

def llm(x):
    return model.invoke(x).content

class Statement(BaseModel):
    response: str = Field(
        ...,
        description="The response to the question",
    )
    reasoning: str = Field(
        ...,
        description="The reasoning behind the response",
    )

def model_response(input) -> Statement:
    completion = model.beta.chat.completions.parse(
        model = os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME"),
        messages = [{"role" : "assistant", "content" : f""" Help me understand the following by giving me a response to the question, a short reasoning on why the response is correct and a rating on the certainty on the correctness of the response:  {input}"""}],
        response_format = Statement)
    
    print(completion.choices[0].message.parsed.reasoning)

    return completion.choices[0].message.parsed


from typing import Dict, TypedDict, Optional
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import random
from typing import Annotated, Sequence, TypedDict

class GraphState(TypedDict):
    objective: Optional[str] = None
    feedback: Optional[str] = None
    history: Optional[str] = None
    code: Optional[str] = None
    specialization: Optional[str]=None
    rating: Optional[str] = None
    iterations: Optional[int]=None
    code_compare: Optional[str]=None
    actual_code: Optional[str]=None
    messages: Annotated[Sequence[BaseMessage], add_messages] = []

workflow = StateGraph(GraphState)

### Nodes

reviewer_start= "You are Code reviewer specialized in {}.\
You need to review the given code following PEP8 guidelines and potential bugs\
and point out issues as bullet list.\
Code:\n {}"

def handle_reviewer(state):
    history = state.get('history', '').strip()
    code = state.get('code', '').strip()
    specialization = state.get('specialization','').strip()
    iterations = state.get('iterations')
    messages = state.get('messages')
    print("Reviewer working...")
    
    feedback = llm(reviewer_start.format(specialization,code))
    messages.append(AIMessage(content="Reviewer: " + feedback))

    return {'history':history+"\n REVIEWER:\n"+feedback,'feedback':feedback,'iterations':iterations+1, 'messages':messages}

coder_start = "You are a Coder specialized in {}.\
Improve the given code given the following guidelines. Guideline:\n {} \n \
Code:\n {} \n \
Output just the improved code and nothing else."
def handle_coder(state):
    history = state.get('history', '').strip()
    feedback = state.get('feedback', '').strip()
    code =  state.get('code','').strip()
    specialization = state.get('specialization','').strip()
    messages = state.get('messages')
    print("CODER rewriting...")
    code = llm(coder_start.format(specialization,feedback,code))
    messages.append(AIMessage(content="Coder: " + code))
    return {'history':history+'\n CODER:\n'+code,'code':code, 'messages':messages}

rating_start = "Rate the skills of the coder on a scale of 10 given the Code review cycle with a short reason.\
Code review:\n {} \n "

code_comparison = "Compare the two code snippets and rate on a scale of 10 to both. Dont output the codes.Revised Code: \n {} \n Actual Code: \n {}"

def handle_result(state):
    print("Review done...")
    messages = state.get('messages')
    history = state.get('history', '').strip()
    code1 = state.get('code', '').strip()
    code2 = state.get('actual_code', '').strip()
    rating  = llm(rating_start.format(history))
    
    code_compare = llm(code_comparison.format(code1,code2))
    messages.append(AIMessage(content="Result: " + code_compare))
    messages.append(AIMessage(content="Code: " + code2))

    return {'rating':rating,'code_compare':code_compare, 'messages':messages}

# Define the nodes we will cycle between
workflow.add_node("handle_reviewer",handle_reviewer)
workflow.add_node("handle_coder",handle_coder)
workflow.add_node("handle_result",handle_result)

classify_feedback = "Are the most important feedback mentioned adressed in the new code? Output just Yes or No.\
Code: \n {} \n Feedback: \n {} \n"
def deployment_ready(state):
    deployment_ready = 1 if 'yes' in llm(classify_feedback.format(state.get('code'),state.get('feedback'))) else 0
    total_iterations = 1 if state.get('iterations')>5 else 0
    return "handle_result" if  deployment_ready or total_iterations else "handle_coder" 


workflow.add_conditional_edges(
    "handle_reviewer",
    deployment_ready,
    {
        "handle_result": "handle_result",
        "handle_coder": "handle_coder"
    }
)

workflow.set_entry_point("handle_reviewer")
workflow.add_edge('handle_coder', "handle_reviewer")
workflow.add_edge('handle_result', END)

app = workflow.compile()

query = "Generate code to train a Regression ML model using a tabular dataset following required preprocessing steps."

specialization = 'python'
code = llm(query)

conversation = app.invoke({"history":code,"code":code,'actual_code':code,"specialization":specialization,'iterations':0},{"recursion_limit":20})

print(conversation)
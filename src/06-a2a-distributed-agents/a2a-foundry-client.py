import asyncio
import logging  # Import the logging module
from typing import Annotated, Any, Literal, Self
from uuid import uuid4
import os
from datetime import datetime
from enum import Enum
import httpx

from a2a.client import A2ACardResolver, A2AClient, create_text_message_object
from a2a.client.errors import A2AClientHTTPError, A2AClientJSONError
from a2a.types import (AgentCard, CancelTaskRequest, CancelTaskResponse, Part,
                       GetTaskPushNotificationConfigRequest,
                       GetTaskPushNotificationConfigResponse, GetTaskRequest,
                       GetTaskResponse, SendMessageRequest, 
                       SendMessageResponse, SendStreamingMessageRequest, MessageSendParams,
                       SendStreamingMessageResponse, PushNotificationConfig, JSONRPCRequest, JSONRPCResponse,
                       SetTaskPushNotificationConfigRequest,
                       SetTaskPushNotificationConfigResponse)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message
from azure.identity import DefaultAzureCredential

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_serializer,
    model_validator,
)

from dotenv import load_dotenv

class TaskState(str, Enum):
    SUBMITTED = 'submitted'
    WORKING = 'working'
    INPUT_REQUIRED = 'input-required'
    COMPLETED = 'completed'
    CANCELED = 'canceled'
    FAILED = 'failed'
    UNKNOWN = 'unknown'

class Message(BaseModel):
    role: Literal['user', 'agent']
    parts: list[Part]
    metadata: dict[str, Any] | None = None

class TaskSendParams(BaseModel):
    id: str
    sessionId: str = Field(default_factory=lambda: uuid4().hex)
    message: Message
    acceptedOutputModes: list[str] | None = None
    pushNotification: PushNotificationConfig | None = None
    historyLength: int | None = None
    metadata: dict[str, Any] | None = None

class SendTaskRequest(JSONRPCRequest):
    method: Literal['tasks/send'] = 'tasks/send'
    params: TaskSendParams


class A2AFoundryClient:
    def __init__(self, credential = None):
        self.credential = credential or DefaultAzureCredential()
    
    def get_access_token(self) -> str:
        token = self.credential.get_token("https://management.azure.com/.default")
        return token.token

    async def get_agent_card(self, agent_url: str) -> AgentCard:

        final_agent_card_to_use: AgentCard | None = None

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__) 

        auth_headers_dict = {"Authorization": "Bearer " + self.get_access_token()}

        # print( auth_headers_dict)

        try:
            async with httpx.AsyncClient() as httpx_client:
                resolver = A2ACardResolver(
                    httpx_client=httpx_client,
                    base_url=agent_url,
                    # agent_card_path uses default, extended_agent_card_path also uses default
                )
                        
                logger.info("A2AResolver initialized.")

                logger.info(f"Attempting to fetch foundry agent card from: {agent_url}")
                _auth_card = await resolver.get_agent_card(
                    http_kwargs={"headers": auth_headers_dict}
                ) 
                logger.info("Successfully fetched foundry agent card:")
                logger.info(_auth_card.model_dump_json(indent=2, exclude_none=True))
                final_agent_card_to_use = _auth_card
      
        except Exception as e:
            logger.error(f"Critical error fetching foundry agent card: {e}", exc_info=True)
            raise RuntimeError("Failed to fetch the foundry agent card. Cannot continue.") from e

        return final_agent_card_to_use

    def create_send_params(self, text: str, task_id: str | None = None, context_id: str | None = None) -> MessageSendParams:
        """Helper function to create the payload for sending a task."""
        send_params: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [{'type': 'text', 'text': text}],
                # 'messageId': uuid4().hex,
                # 'kind': 'message',

            },
            'Id': uuid4().hex,
            'configuration': {
                'acceptedOutputModes': ['text'],
            }
        }

        if task_id:
            send_params['message']['taskId'] = task_id
        else:
            send_params['message']['taskId'] = uuid4().hex

        if context_id:
            send_params['message']['contextId'] = context_id
        else:
            send_params['message']['contextId'] = uuid4().hex
        
        return MessageSendParams(**send_params)


    async def send_message_to_agent(self, agent_card: AgentCard, message: str) -> Any:
        """Send a message to the agent and return the response."""

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__) 

        response = ''

        auth_headers_dict = {"Authorization": "Bearer " + self.get_access_token()}

        try:
            async with httpx.AsyncClient() as httpx_client:
                client = A2AClient(
                    httpx_client=httpx_client,
                    agent_card=agent_card,
                )
                        
                logger.info("A2AClient initialized.")

                logger.info(f"Attempting to send message to foundry agent card from: {agent_card.name}")
                send_params = MessageSendParams(
                    message=create_text_message_object(content=message),
                )

                request = SendMessageRequest(id=uuid4().hex, params=send_params)
                logger.info(f"Sending message: {send_params.model_dump_json(exclude_none=True)}")

                send_message_response = await client.send_message(request, http_kwargs={"headers": auth_headers_dict})
                response = send_message_response.root.result
                print(f'\n{response.model_dump_json(exclude_none=True)}')
            
        except Exception as e:
            logger.error(f"Critical error sending message to foundry agent card: {e}", exc_info=True)
            raise RuntimeError("Failed to send message the foundry agent card. Cannot continue.") from e

        return response
    

    async def send_task_to_agent(self, agent_card: AgentCard, message: str) -> Any:
        """Send a message to the agent and return the response."""

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__) 

        response = ''

        auth_headers_dict = {"Authorization": "Bearer " + self.get_access_token()}

        try:
            async with httpx.AsyncClient() as httpx_client:
                client = A2AClient(
                    httpx_client=httpx_client,
                    agent_card=agent_card,
                )
                        
                logger.info("A2AClient initialized.")

                task_id = f"{uuid4().hex}"
                logger.info(f"Attempting to send task to foundry agent card from: {agent_card.name}")

                send_task_params = {
                    "id": task_id,
                    "message": {
                        'role': 'user',
                        'parts': [{'type': 'text', 'text': message}],
                    },
                    "http_kwargs": {"headers": auth_headers_dict},
                }

                request = SendTaskRequest(params=send_task_params)

                response = SendTaskResponse(**await client._send_request(request))
                print(f'\n{response.model_dump_json(exclude_none=True)}')
            
        except Exception as e:
            logger.error(f"Critical error sending message to foundry agent card: {e}", exc_info=True)
            raise RuntimeError("Failed to send message the foundry agent card. Cannot continue.") from e

        return response
    

async def main() -> None:
    load_dotenv()

    azure_foundry_agent_url = os.getenv("AZURE_FOUNDRY_AGENT_URL")
    if not azure_foundry_agent_url:
        raise ValueError("AZURE_FOUNDRY_AGENT_URL environment variable is not set")
    logging.basicConfig(level=logging.INFO) # Set up logging        
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('__main__').setLevel(logging.WARNING)
    logging.getLogger('azure.identity').setLevel(logging.WARNING)
    logging.getLogger('a2a.client').setLevel(logging.WARNING)

    a2a_client = A2AFoundryClient()
    agent_card = await a2a_client.get_agent_card(agent_url=azure_foundry_agent_url)
    print("Agent card retrieved successfully:")
    print(agent_card.model_dump_json(indent=2, exclude_none=True))

    response = await a2a_client.send_task_to_agent(agent_card, "Hello, Foundry Agent!")
    print("Response from agent:")
    print(response)

# Usage example
if __name__ == "__main__":
    asyncio.run(main()) 

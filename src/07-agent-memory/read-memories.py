import os
from mem0 import Memory
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# Load Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME = os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME")
AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")

# Load Azure AI Search configuration
SEARCH_SERVICE_ENDPOINT = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
SEARCH_SERVICE_API_KEY = os.getenv("AZURE_AI_SEARCH_KEY")
SEARCH_SERVICE_NAME = os.getenv("AZURE_AI_SEARCH_NAME")

# Create Azure OpenAI client
azure_openai_client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2024-10-21"
)

memory_config = {
    "vector_store": {
        "provider": "azure_ai_search",
        "config": {
            "service_name": SEARCH_SERVICE_NAME,
            "api_key": SEARCH_SERVICE_API_KEY,
            "collection_name": "memories",
            "embedding_model_dims": 1536,
        },
    },
    "embedder": {
        "provider": "azure_openai",
        "config": {
            "model": AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME,
            "embedding_dims": 1536,
            "azure_kwargs": {
                "api_version": "2024-10-21",
                "azure_deployment": AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL_NAME,
                "azure_endpoint": AZURE_OPENAI_ENDPOINT,
                "api_key": AZURE_OPENAI_API_KEY,
            },
        },
    },
    "llm": {
        "provider": "azure_openai",
        "config": {
            "model": AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME,
            "temperature": 0.1,
            "max_tokens": 2000,
            "azure_kwargs": {
                "azure_deployment": AZURE_OPENAI_CHAT_COMPLETION_DEPLOYED_MODEL_NAME,
                "api_version": "2024-10-21",
                "azure_endpoint": AZURE_OPENAI_ENDPOINT,
                "api_key": AZURE_OPENAI_API_KEY,
            },
        },
    },
    "version": "v1.1",
}

# Initialize memory
memory = Memory.from_config(memory_config)
print("Mem0 initialized with Azure AI Search")


all_memories = memory.get_all(user_id="demo_user")
print(f"Total memories: {len(all_memories['results'])}")

search_query = "What can you tell me about my experience in building serverless agents?"
search_results = memory.search(search_query, user_id="demo_user")
print(f"Found {len(search_results['results'])} relevant memories:")
for i, result in enumerate(search_results['results'][:3], 1):
    print(f"{i}. {result['memory']} (Score: {result['score']:.4f})")
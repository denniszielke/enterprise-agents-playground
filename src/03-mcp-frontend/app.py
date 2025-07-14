import logging
import os
import json
import requests
from pathlib import Path
from aiohttp import web
from azure.core.credentials import AzureKeyCredential
from azure.identity import AzureDeveloperCliCredential, DefaultAzureCredential
from dotenv import load_dotenv
from msal import ConfidentialClientApplication
import msal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-client")

entra_client_app : ConfidentialClientApplication = None

global_token_cache = msal.TokenCache() 




async def create_app():
    global entra_client_app, global_token_cache
    
    if not os.environ.get("RUNNING_IN_PRODUCTION"):
        logger.info("Running in development mode, loading from .env file")
        load_dotenv()

    app = web.Application()

    client_id = os.environ.get("ENTRA_MCP_CLIENT_APP_ID")
    client_secret = os.environ.get("ENTRA_MCP_CLIENT_APP_SECRET")
    tenant_id = os.environ.get("ENTRA_TENANT_ID")
    tenant_name = os.environ.get("ENTRA_TENANT_NAME", "fdpo.onmicrosoft.com")
    authority = f"https://login.microsoftonline.com/{tenant_name}"

    entra_client_app = ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret,
        token_cache=global_token_cache
    )

    # Serve static files and index.html
    current_directory = Path(__file__).parent  # Points to 'app' directory
    static_directory = current_directory / 'static'

    # Ensure static directory exists
    if not static_directory.exists():
        raise FileNotFoundError("Static directory not found at expected path: {}".format(static_directory))

    # Serve index.html at root
    async def index(request):
        return web.FileResponse(static_directory / 'index.html')

    app.router.add_get('/', index)
    app.router.add_static('/static/', path=str(static_directory), name='static')
    app.router.add_post('/api/list_mcp_tools', list_mcp_tools)

    return app

async def list_mcp_tools(request):
    """Endpoint to list MCP tools"""
    try:
        scope = ["https://graph.microsoft.com/.default"]

        result = entra_client_app.acquire_token_for_client(scopes=scope)
        # result = entra_client_app.acquire_token_by_device_flow

        if "access_token" in result:
            print("Token was obtained from:", result["token_source"])  # Since MSAL 1.25
            print("Access token:", result["access_token"])
            # Calling graph using the access token
            # graph_data = requests.get(  # Use token to call downstream service
            #     config["endpoint"],
            #     headers={'Authorization': 'Bearer ' + result['access_token']},).json()
            # print("Graph API call result: %s" % json.dumps(graph_data, indent=2))
        else:
            print("Token acquisition failed", result)  # Examine result["error_description"] etc. to diagnose error

        # Here you would implement the logic to list MCP tools
        # For now, we return a dummy response
        return web.json_response({"tools": ["tool1", "tool2", "tool3"]})
    except Exception as e:
        logger.error(f"Error listing MCP tools: {e}")
        return web.json_response({"error": str(e)}, status=500)

if __name__ == "__main__":
    host = os.environ.get("HOST", "localhost")
    port = int(os.environ.get("PORT", 8765))
    web.run_app(create_app(), host=host, port=port)

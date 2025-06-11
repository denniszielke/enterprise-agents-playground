import asyncio
import pytz
from datetime import datetime
from dotenv import load_dotenv
from typing import Any

from typing import List
from fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

load_dotenv()

mcp = FastMCP("DateTimeSpace")

users = {
    "Dennis": {
        "name": "Dennis",
        "location": "Europe/Berlin",
    },
    "John": {
        "name": "John",
        "location": "America/New_York",
    },
}

@mcp.resource("config://version")
def get_version() -> dict: 
    return {
        "version": "1.2.0",
        "features": ["tools", "resources"],
    }

@mcp.tool()
async def get_current_user() -> str:
    """Get the username of the current user."""
    return "Dennis"

@mcp.tool()
def get_current_location(username: str) -> str:
    """Get the current timezone location of the user for a given username."""
    print(username)
    if username in users:
        return users[username]["location"]
    else:
        return "Europe/London"

@mcp.tool()
def get_current_time(location: str) -> str:
    """Get the current time in the given location. The pytz is used to get the timezone for that location. Location names should be in a format like America/Seattle, Asia/Bangkok, Europe/London. Anything in Germany should be Europe/Berlin"""
    try:
        print("get current time for location: ", location)
        location = str.replace(location, " ", "")
        location = str.replace(location, "\"", "")
        location = str.replace(location, "\n", "")
        # Get the timezone for the city
        timezone = pytz.timezone(location)

        # Get the current time in the timezone
        now = datetime.now(timezone)
        current_time = now.strftime("%I:%M:%S %p")

        return current_time
    except Exception as e:
        print("Error: ", e)
        return "Sorry, I couldn't find the timezone for that location."
    

@mcp.tool()
async def move(username: str, newlocation: str) -> bool:
    """Move the user to a new location. Returns true if the user was moved successfully, false otherwise."""
    if username in users:
        users[username]["location"] = newlocation
        return True
    else:
        return False

@mcp.prompt()
def get_user_time(username: str) -> list[base.Message]:
    """Find out the current time for a user. This prompt is used to get the current time for a user in their location.
    Args:
        username: The username of the user
    """

    return [
        base.Message(
            role="user",
            content=[
                base.TextContent(
                    text=f"I'm trying to find the local time for the user'{username}. "
                    f"How can I find this out? Please provide step-by-step troubleshooting advice."
                )
            ]
        )
    ]

async def check_mcp(mcp: FastMCP):
    # List the components that were created
    tools = await mcp.get_tools()
    resources = await mcp.get_resources()
    templates = await mcp.get_resource_templates()
    
    print(
        f"{len(tools)} Tool(s): {', '.join([t.name for t in tools.values()])}"
    )
    print(
        f"{len(resources)} Resource(s): {', '.join([r.name for r in resources.values()])}"
    )
    print(
        f"{len(templates)} Resource Template(s): {', '.join([t.name for t in templates.values()])}"
    )
    
    return mcp

if __name__ == "__main__":
    try:
        # asyncio.run(check_mcp(mcp))
        mcp.run(transport="sse", host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Cleaning up...")
    except Exception as e:
        print(f"An error occurred: {e}")
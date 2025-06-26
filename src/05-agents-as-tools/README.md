# Dynamic agent as tools via MCP

The objective of this lab is to learn how one agent can dynamically discover other agents and delegate tasks to them

The azure foundry mcp server can be found here: https://github.com/azure-ai-foundry/mcp-foundry

## Steps

1. Clone the MCP server
```
git clone https://github.com/azure-ai-foundry/mcp-foundry.git
```

2. Execute the react agent to use the agents in the MCP server

```
python mcp-foundry-react.py
```


```bash
# Setup environment with uv
uv venv
source .venv/bin/activate  # On macOS/Linux

# Install dependencies
uv add mcp==1.9.4 azure-identity==1.23.0 python-dotenv==1.1.0 azure-ai-projects==1.0.0b11 azure-ai-agents==1.1.0b2 aiohttp 

# Run server (F)
uv run -m azure_agent_mcp_server
```
# Connecting Claude Desktop to the NovaFlow MCP server

1. Start the backend: `uvicorn backend.main:app --reload`
2. Add this to Claude Desktop's `claude_desktop_config.json`
   (for the Microsoft Store version it sits under
   `AppData\Local\Packages\Claude_...\LocalCache\Roaming\Claude`):

```json
"mcpServers": {
  "novaflow": {
    "command": "<project>\\venv\\Scripts\\python.exe",
    "args": ["<project>\\mcp_server\\server.py"]
  }
}
```

3. Fully quit and reopen Claude Desktop. Requires `mcp<2` (tested with 1.30.0).
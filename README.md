# WORK IN PROGRESS - USE WITH CAUTION - Windows

# MCP Tool Builder
An MCP server that empowers LLMs to dynamically create new tools through MCP clients such as Claude Desktop.

## Features
- Create new tools by describing them in natural language
  - Requires client restart to use new tools (Claude Desktop)
- New tools are saved as python scriptlets in ...\\mcp-tool-builder\\tools
- New tool definitions are saved in ...\\mcp-tool-builder\\tools\tools.json

## Example tools included at installation
get_bitcoin_price: Fetches current Bitcoin price from CoinGecko
get_temperature: Gets temperature for US ZIP codes

## Creating New Tools
Use the create_tool command in Claude Desktop (or suggest strongly!!) to create new tools dynamically

## Installation
1. Clone this repository
2. Install dependencies:
```bash
cd mcp-tool-builder
uv venv
.venv\Scripts\activate
uv pip install -e .
```

## Usage with Claude Desktop
Add to `claude_desktop_config.json`:

```json
{
    "mcpServers": {
        "tool-builder": {
            "command": "uv",
            "args": [
                "--directory", 
                "PATH_TO\\mcp-tool-builder",
                "run",
                "tool-builder"
            ]
        }
    }
}
import os
import json
import ast
import inspect
import importlib.util
from typing import Any, Dict, List, Optional
from pathlib import Path

from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
import mcp.types as types

class ToolBuilderServer:
    def __init__(self, tools_dir: str):
        """Initialize the Tool Builder Server.
        
        Args:
            tools_dir: Directory where tool scripts will be stored
        """
        self.tools_dir = Path(tools_dir)
        self.tools: Dict[str, Any] = {}
        self.tools_config: List[Dict] = []
        
        # Create tools directory if it doesn't exist
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing tools
        self.reload_tools()
        
        # Initialize MCP server
        self.server = Server("tool-builder")
        self._register_handlers()

    def _register_handlers(self):
        """Register all MCP protocol handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List all available tools including tool management tools."""
            tools = [
                types.Tool(
                    name="create_tool",
                    description="Create a new Python tool with specified functionality",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tool_name": {
                                "type": "string",
                                "description": "Name of the new tool"
                            },
                            "description": {
                                "type": "string", 
                                "description": "Description of what the tool should do"
                            },
                            "code": {
                                "type": "string",
                                "description": "Python code implementing the tool"
                            }
                        },
                        "required": ["tool_name", "description", "code"]
                    }
                ),
                types.Tool(
                    name="list_available_tools",
                    description="List all currently available tools",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                # Add existing tools dynamically
                *[types.Tool(
                    name=tool["name"],
                    description=tool.get("description", "No description available"),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            param: {"type": "string"} 
                            for param in tool.get("parameters", {})
                        },
                        "required": list(tool.get("parameters", {}).keys())
                    }
                ) for tool in self.tools_config]
            ]
            return tools

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict | None
        ) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Handle tool execution requests."""
            if not arguments:
                arguments = {}

            if name == "create_tool":
                result = await self._create_tool(
                    arguments["tool_name"],
                    arguments["description"],
                    arguments["code"]
                )
                return [types.TextContent(
                    type="text",
                    text=result
                )]

            elif name == "list_available_tools":
                tools_list = "\n".join([
                    f"- {tool['name']}: {tool.get('description', 'No description')}"
                    for tool in self.tools_config
                ])
                return [types.TextContent(
                    type="text",
                    text=f"Available tools:\n{tools_list}"
                )]

            # Handle dynamically loaded tools
            elif name in self.tools:
                # Check if the tool is properly loaded
                if name not in self.tools or self.tools[name] is None:
                    return [types.TextContent(
                        type="text",
                        text=(f"Tool '{name}' exists but cannot be used yet.\n"
                              "IMPORTANT: New tools require a client restart before they can be used.\n"
                              "Please:\n"
                              "1. Restart Claude Desktop\n"
                              "2. Start a new conversation\n"
                              "3. Try using the tool again")
                    )]

                try:
                    tool_func = self.tools[name]
                    if inspect.iscoroutinefunction(tool_func):
                        result = await tool_func(**arguments)
                    else:
                        result = tool_func(**arguments)
                    return [types.TextContent(
                        type="text",
                        text=str(result)
                    )]
                except Exception as e:
                    return [types.TextContent(
                        type="text",
                        text=f"Error executing tool {name}: {str(e)}"
                    )]
            else:
                return [types.TextContent(
                    type="text",
                    text=(f"Tool {name} not found or not fully initialized. "
                        "Please ensure the tool was created correctly "
                        "and restart Claude Desktop.")
                )]

    async def _create_tool(self, tool_name: str, description: str, code: str) -> str:
        try:
            # Validate the code is Python
            try:
                ast.parse(code)
            except SyntaxError:
                return f"Error: Invalid Python syntax in the tool code for {tool_name}"

            if any(tool["name"] == tool_name for tool in self.tools_config):
                return f"Tool {tool_name} already exists"

            tool_path = self.tools_dir / f"{tool_name}.py"
            tool_path.write_text(code)

            # Parse the function definition
            tree = ast.parse(code)
            func_def = next(
                (node for node in ast.walk(tree) 
                if isinstance(node, ast.FunctionDef) and node.name == tool_name), 
                None
            )

            if not func_def:
                return f"Error: Could not find a function named {tool_name} in the provided code"

            # Extract parameters
            parameters = {
                arg.arg: "string" 
                for arg in func_def.args.args 
                if arg.arg != "self"
            }

            tool_config = {
                "name": tool_name,
                "description": description,
                "parameters": parameters,
                "file": f"{tool_name}.py",  # Store relative path
                "function": tool_name
            }
            self.tools_config.append(tool_config)
            
            tools_json_path = self.tools_dir / "tools.json"
            tools_json_path.write_text(json.dumps(self.tools_config, indent=4))

            self.reload_tools()
                        
            # Return success message with explicit restart instructions
            return (f"Tool '{tool_name}' has been successfully created and will be available after client restart.\n"
                f"Description: {description}\n"
                f"Status: Added to tools.json\n"
                "IMPORTANT: You must restart Claude Desktop before you can use this tool.\n"
                "Please restart the client before attempting to use the newly created tool.")

        except Exception as e:
            # Ensure a string is always returned, even in error cases
            return f"Error creating tool: {str(e)}" or "Unknown tool creation error"

    def reload_tools(self):
        try:
            tools_json_path = self.tools_dir / "tools.json"
            if tools_json_path.exists():
                self.tools_config = json.loads(tools_json_path.read_text())
            else:
                self.tools_config = []

            self.tools.clear()
            for tool in self.tools_config:
                try:
                    # Resolve relative path
                    tool_path = self.tools_dir / tool["file"]
                    spec = importlib.util.spec_from_file_location(
                        tool["name"], 
                        str(tool_path)
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        tool_func = getattr(module, tool["function"])
                        self.tools[tool["name"]] = tool_func
                    else:
                        print(f"Could not load module for tool {tool['name']}")
                        self.tools[tool["name"]] = None
                except Exception as e:
                    print(f"Error loading tool {tool['name']}: {e}")
                    # Explicitly set to None to prevent execution
                    self.tools[tool["name"]] = None

        except Exception as e:
            print(f"Error reloading tools: {e}")

async def main():
    import argparse
    from pathlib import Path
    
    # Get project root directory (parent of src)
    project_root = Path(__file__).parent.parent.parent
    default_tools_dir = project_root / "tools"
    
    parser = argparse.ArgumentParser(description='Tool Builder MCP Server')
    parser.add_argument('--tools-dir', type=str, default=str(default_tools_dir),
                       help='Directory where tool scripts will be stored')
    
    args = parser.parse_args()
    server = ToolBuilderServer(tools_dir=args.tools_dir)
    
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options(
                notification_options=NotificationOptions(),
                experimental_capabilities={}
            )
        )

if __name__ == "__main__":
    import asyncio
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
import asyncio
from .tool_builder_server import main

def run_server():
    asyncio.run(main())
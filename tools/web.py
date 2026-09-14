import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import asyncio
from langchain.mcp import MCPAdapter
from config.settings import BROWSER_OS_URL
async def main():
    async with MCPAdapter(BROWSER_OS_URL) as mcp:
        tools= await mcp.list_tools()
        print(type(tools))
if __name__ == "__main__":
    asyncio.run(main())
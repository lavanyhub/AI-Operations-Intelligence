import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    name = sys.argv[1] if len(sys.argv) > 1 else None
    args = dict(a.split("=", 1) for a in sys.argv[2:])   # example: month=2026-10
    params = StdioServerParameters(command=sys.executable, args=["mcp_server/server.py"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("Tools found:", [t.name for t in tools.tools])
            if name:
                result = await session.call_tool(name, args)
                for block in result.content:
                    print("Result:", block.text)


asyncio.run(main())
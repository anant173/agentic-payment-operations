# mcp-client.py
# pip install fastmcp
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from dotenv import load_dotenv
load_dotenv()
import json, os

# You can pass any custom headers to MCP servers using the x-tfy-mcp-headers header.
# This is useful for authentication tokens, metadata, or any headers your MCP server needs.
#
# For Remote MCP Servers:
# - Pass headers as a JSON string: {"Authorization": "Bearer token"}
# - Headers will be applied to all requests to the MCP server
#
# Example usage:
# passthroughHeaders = {"Authorization": "Bearer token"}

async def main():
    token = os.getenv("TFY_API_KEY")
    url = os.getenv("TFY_SLACK_MCP_URL")
    transport = StreamableHttpTransport(
        url=url,
        headers={"Authorization": f"Bearer {token}"}
        # auth=token,
        # headers={"x-tfy-mcp-headers": json.dumps(passthroughHeaders)}
    )
    async with Client(transport=transport) as client:
        tools = await client.list_tools()
        for tool in tools:
            print(f"Tool: {tool.name}")
            print(f"Description: {tool.description}")
            print(f"Parameters: {json.dumps(tool.inputSchema, indent=2)}")
            print("-" * 60)

        # --- Optional: Test Slack call ---
            # Uncomment to test real invocation
            #
            # print("\n🚀 Testing getConversations...\n")
            # result = await client.call_tool(
            #     "getConversations",
            #     {"types": "public_channel", "limit": 5},
            # )
            # print("Result:", json.dumps(result, indent=2))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

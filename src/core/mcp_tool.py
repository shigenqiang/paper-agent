##使用MCP服务

##fastmcp是用来写服务器的， 在客户端配置多个服务器
from langchain_mcp_adapters.client import MultiServerMCPClient
import  asyncio

async def get_mcp_tools():
    client = MultiServerMCPClient({
        "paper": {
            "transport": "stdio",
            "command": "python",
            "args": ["-m", "paper_for_search.paper_search_mcp.server"]}
    })
    return await client.get_tools()

asyncio.run(get_mcp_tools())



if __name__ == "__main__":
    import asyncio
    from langchain_mcp_adapters.client import MultiServerMCPClient

    async def main():
        client = MultiServerMCPClient({
            "paper": {
                "transport": "stdio",   # 👈 关键
                "command": "python",
                "args": ["-m", "paper_for_search.paper_search_mcp.server"]
            }
        })

        tools = await client.get_tools()

        for t in tools:
            print(t.name, ":", t.description)

    asyncio.run(main())


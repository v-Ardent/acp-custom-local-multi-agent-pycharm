from mcp.server import MCPServer

mcp = MCPServer("Bookshop")

@mcp.tool()
def add(a: int, b: int) -> int:
 """Add two numbers."""
 return a + b

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8000,
    )


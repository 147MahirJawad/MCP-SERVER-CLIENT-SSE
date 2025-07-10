import os
import subprocess
from mcp.server.fastmcp import FastMCP
from mcp.server import Server
from mcp.server.sse import SseServerTransport

from dotenv import load_dotenv
from typing import Dict, List

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from tavily import TavilyClient
import uvicorn
load_dotenv()
mcp = FastMCP("terminal")

DEFAULT_WORKSPACE = "D:/OFFICE PENTA/New folder/mcp-sse/mcp_workspace"
os.makedirs(DEFAULT_WORKSPACE, exist_ok=True)


@mcp.tool()
async def run_command(command: str) -> str:
    """
    Executes a shell command in the default workspace and returns
    the result.
    
    Args:
        command (str): A shell command like 'ls', 'pwd', etc.

    Returns:
        str: Standard output or error message from
        running the command.
    """
    try:
        result = subprocess.run(
            shell=True,
            cwd=DEFAULT_WORKSPACE,
            capture_output=True,
            text=True 
                                           
       )
        return result.stdout or result.stderr
    except Exception as e:
        return str(e)

if "TAVILY_API_KEY" not in os.environ:
    raise Exception("TAVILY_API_KEY environment variable not set")
tavily_client = TavilyClient(os.environ["TAVILY_API_KEY"])

@mcp.tool()
def web_search(query: str) -> List[Dict]:
    """
        Search the web using Tavily Web Search API.
    Args:
        query (str): The search query string.
    Returns:
        List[Dict]: A list of search results, each containing 
        title, link, and snippet
    """
    try:
        response = tavily_client.search(query)
        return response["results"]
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
async def add_numbers(a: float, b:float) -> float:
    """
    Adds two numbers together.
    
    Args:
        a (float): First number.
        b (float): Second number.
    
    Returns:
        float: The sum of a and b.
    """
    return a + b

# Create a Starlette app with the MCP server

def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """
    Create a Starlette app with SSE and message endpoints.
    
    Args:
        mcp_server (Server): The core MCP server instance.
        debug (bool): Enable debug mode for verbose logging.
    Returns:
        Starlette: The configured Starlette application.
    """
    
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
       """
       Handles a new SSE client connection and links it to the MCP server.
       """ 

       async with sse.connect_sse(
           request.scope,
           request.receive,
           request._send,
       ) as (read_stream,write_stream):
           await mcp_server.run(
               read_stream,
               write_stream,
               mcp_server.create_initialization_options(),

           )
    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint = handle_sse),
            Mount("/messages/", app=sse.handle_post_message)
            ],
        )
    
if __name__ == "__main__":
    
    mcp_server= mcp._mcp_server

    import argparse
    parser = argparse.ArgumentParser(description="Run MCP server with SSE support")
    parser.add_argument('--host', default='0.0.0.0', help='Host to run the server on')
    parser.add_argument('--port', type=int, default=8081, help='Port to run the server on')
    args = parser.parse_args()

    starlette_app = create_starlette_app(mcp_server, debug=True)

    uvicorn.run(starlette_app, host=args.host, port=args.port)
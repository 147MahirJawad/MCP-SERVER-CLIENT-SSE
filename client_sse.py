import asyncio
import os
import json
import sys
from typing import Optional

from mcp import ClientSession

from mcp.client.sse import sse_client

from google import generativeai
from google.generativeai import types
from google.generativeai.types import Tool, FunctionDeclaration
from google.generativeai.types import GenerationConfig

from dotenv import load_dotenv

load_dotenv()
generativeai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class MCPClient:
    def __init__(self):
        """
        Initialize the MCP client.
        
        This constructor sets up:
        - The Gemini Ai client using API key from the environment variables.
        - Placeholders for the client session and the stream context(which manages the SSE connection).

        The Gemini client is used to generate content and can request tool calls from MCP server.

        """
        self.session: Optional[ClientSession] = None

        self._streams_context = None
        self._session_context = None

        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")  


    async def connect_to_sse_server(self, server_url: str):
        """
        Connect to an MCP server that uses SSE transport.
        
        Steps performed in this function:
        1. Open an SSE connection using provided server URL.
        2. Use the connection streams to create an MCP ClientSession.
        3. Initialize the MCP session, which sets up the protocol for communication.
        4. Retrieve and display the list of available tools from MCP server.
        
        Args:
            server_url (str): The URL of the MCP server to connect to that supports SSE.

            """    
        self._streams_context = sse_client(url=server_url)

        streams = await self._streams_context.__aenter__()

        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()

        await self.session.initialize()

        print("Initialized SSE client.......")
        print("Available tools:")
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

        self.function_declarations = convert_mcp_tools_to_gemini(tools)

              
    async def cleanup(self):
        """
        Clean up resources by properly closing the SSE session and stream contexts.
        
        As we used asynchronous context managers(which are like 'with' blocks for async code), we need to
        Clean up by closing the session and stream contexts. This ensures that all resources are released properly.
        """
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None) 




    async def process_query(self, query: str) -> str:
        user_prompt_content = {"role": "user", "parts": [{"text": query}]}

        model = generativeai.GenerativeModel(
            model_name="gemini-1.5-flash",
            tools=self.function_declarations
        )

        # Step 1: Initial generation
        response = model.generate_content([user_prompt_content])
        final_text = []

        for candidate in response.candidates:
            if candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        tool_name = part.function_call.name
                        try:
                            tool_args = dict(part.function_call.args)
                        except Exception as e:
                            print(f"[Tool args conversion error]: {e}")
                            tool_args = {}

                        print(f"\n[Gemini requested tool call: {tool_name} with args {tool_args}]")

                        try:
                            result = await self.session.call_tool(tool_name, tool_args)
                            # Convert result to string representation
                            if isinstance(result, (list, dict)):
                                # Serialize complex objects to JSON
                                function_response = json.dumps(result)
                            else:
                                # Convert simple types to string
                                function_response = str(result)
                        except Exception as e:
                            function_response = f"Tool error: {str(e)}"

                        # Create tool response content
                        function_response_content = {
                            "role": "function",
                            "parts": [{
                                "function_response": {
                                    "name": tool_name,
                                    "response": {
                                    "content": function_response  
                                }
                                }
                            }]
                        }

                        # Properly formatted function call content
                        function_call_content = {
                            "role": "model",
                            "parts": [{
                                "function_call": {  
                                    "name": tool_name,
                                    "args": tool_args
                                }
                            }]
                        }

                        # Send back user query, Gemini's tool call, and tool response
                        response = model.generate_content([
                            user_prompt_content,
                            function_call_content,
                            function_response_content
                        ])

                        if response.candidates and response.candidates[0].content.parts:
                            final_text.append(response.candidates[0].content.parts[0].text)
                    else:
                        final_text.append(part.text)

        return '\n'.join(final_text)

    
    async def chat_loop(self):
        """
        Run an interactive chat loop in the terminal.
        
        This function allows the user to type queries one after the other. The loop continues until the user types 'exit'.
        Each query is processed using the process_query method, and the response is printed in the console.
        """
        print("\nMCP Client Started! Type 'exit' to quit.\n"
              )
        while True:
            query = input("\nEnter your query: ").strip()
            if query.lower() == 'exit':
                print("Exiting chat loop.")
                break

            response = await self.process_query(query)
            print(f"\nResponse: {response}\n")


def clean_schema(schema):
    """
    Recursively remove 'title' fields from a JSON schema.
    
    Some JSON schemas include 'title' field that is not needed for our tool function calls.
    This function goes through the schema and removes any 'title' entries, including nested ones.
    
    Args:
        schema (dict): The JSON schema to clean and represented as a dictionary.
        
    Returns:
        dict: The cleaned schema without 'title' fields.
    """

    if isinstance(schema, dict):
        schema.pop('title', None)
        
        if 'properties' in schema and isinstance(schema["properties"], dict):
            for key in schema['properties']:
                schema['properties'][key] = clean_schema(schema["properties"][key])
                
    return schema  

def convert_mcp_tools_to_gemini(mcp_tools):
    """
    Convert MCP tools to Gemini function declarations.
    
    Each MCP tool contains information such as name, description, and an input JSON schema.
    This function cleans the JSON schema by removing unnecessary fields and then creats a Gemini function.
    The function declarations are then wrapped in Gemini Tool objects.

    Args:
        mcp_tools (list): A list of MCP tool objects with attributes 'name','description' and 'inputSchema'.

    Returns:
        list: A list of Gemini Tool objects ready for function calling.

    """
    gemini_tools = []

    for tool in mcp_tools:
        parameters = clean_schema(tool.inputSchema)
        
        # Add description about return type
        description = tool.description + " The tool returns its result as a string."
        
        function_declaration = FunctionDeclaration(
            name=tool.name,
            description=description,
            parameters=parameters
        )

        gemini_tool = Tool(function_declarations=[function_declaration])
        gemini_tools.append(gemini_tool)

    return gemini_tools

async def main():
    """
    Main entry point for the client.
    
    This function:
    -Checks that a server URL is provided as a command-line argument
    -Creates an instance of MCPClient.
    -Connects to the MCP server via SSE.
    -Enters an interactive chat loop to process user queries.
    -Cleans up all resources when finished.
    
    Usage:
    
        Python client_sse.py <server_url>
        
    """
    if len(sys.argv) < 2:
        print("Usage: python client_sse.py <server_url>")
        sys.exit(1)


    client = MCPClient()

    try:

        await client.connect_to_sse_server(sys.argv[1])

        await client.chat_loop()

    finally:

        await client.cleanup()

if __name__=="__main__":

    asyncio.run(main())

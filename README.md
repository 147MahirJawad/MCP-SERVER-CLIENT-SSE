# MCP SSE Client-Server System

## Overview

This project implements a client-server system using Server-Sent Events (SSE) for real-time communication between a Gemini AI-powered client and a tool-providing server. The system allows users to interact with various tools (like web search and command execution) through natural language queries processed by Gemini AI.

## Features

- **SSE-based Communication**: Real-time, bidirectional communication between client and server
- **Gemini AI Integration**: Natural language processing for tool selection and query understanding
- **Tool Ecosystem**: Includes tools for:
  - Web search (via Tavily API)
  - Shell command execution
  - Basic arithmetic operations
- **Asynchronous Architecture**: Built with Python's asyncio for efficient I/O operations

## Prerequisites

- Python 3.7+
- Required environment variables:
  - `GEMINI_API_KEY` - For Gemini AI access
  - `TAVILY_API_KEY` - For web search functionality

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/147MahirJawad/mcp-server-client-sse.git
   cd mcp-sse-system
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your API keys:
   ```
   GEMINI_API_KEY=your_gemini_key
   TAVILY_API_KEY=your_tavily_key
   ```

## Usage

### Running the Server

Start the MCP server with:
```bash
python server_sse.py --host 0.0.0.0 --port 8081
```

Optional arguments:
- `--host`: Server host (default: 0.0.0.0)
- `--port`: Server port (default: 8081)

### Running the Client

Connect to the server with:
```bash
python client_sse.py http://localhost:8081/sse
```

Once connected, you can:
- Enter natural language queries
- The system will automatically select and use appropriate tools
- Type 'exit' to quit

### Available Tools

1. **Web Search**: Performs web searches using Tavily API
   - Example: "Search for latest AI news"

2. **Run Command**: Executes shell commands in a workspace directory
   - Example: "List files in the workspace"

3. **Add Numbers**: Performs basic arithmetic
   - Example: "What's 123 plus 456?"

## Architecture

```
Client (Gemini AI) ↔ SSE Transport ↔ MCP Server ↔ Tools
```

- **Client**: Uses Gemini AI to interpret user queries and select tools
- **SSE Transport**: Handles real-time communication
- **MCP Server**: Manages tool execution and responses
- **Tools**: Various functionality endpoints

## Configuration

- Workspace directory can be modified in `server_sse.py` (DEFAULT_WORKSPACE)
- Additional tools can be added by decorating functions with `@mcp.tool()`

## Troubleshooting

- Ensure all API keys are set in `.env`
- Verify server is running before starting client
- Check port availability if connection fails

## License

[MIT License](LICENSE)

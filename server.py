import argparse
import asyncio
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

import tools.flows
import tools.records
import tools.schema

app = Server("salesforce-mcp")


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="query_records",
            description="Run a SOQL query against Salesforce. Returns a list of matching records.",
            inputSchema={
                "type": "object",
                "properties": {
                    "soql": {
                        "type": "string",
                        "description": "A valid SOQL query, e.g. SELECT Id, Name FROM Account LIMIT 10",
                    }
                },
                "required": ["soql"],
            },
        ),
        Tool(
            name="get_record",
            description="Fetch a single Salesforce record by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Salesforce object API name, e.g. Account"},
                    "record_id": {"type": "string", "description": "18-character Salesforce record ID"},
                },
                "required": ["object_name", "record_id"],
            },
        ),
        Tool(
            name="create_record",
            description="Create a new Salesforce record. Use describe_object first to check available fields.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Salesforce object API name, e.g. Contact"},
                    "fields": {"type": "object", "description": "Field name/value pairs for the new record"},
                },
                "required": ["object_name", "fields"],
            },
        ),
        Tool(
            name="update_record",
            description="Update fields on an existing Salesforce record.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string"},
                    "record_id": {"type": "string"},
                    "fields": {"type": "object", "description": "Field name/value pairs to update"},
                },
                "required": ["object_name", "record_id", "fields"],
            },
        ),
        Tool(
            name="delete_record",
            description="Delete a Salesforce record by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string"},
                    "record_id": {"type": "string"},
                },
                "required": ["object_name", "record_id"],
            },
        ),
        Tool(
            name="list_objects",
            description="List all queryable Salesforce objects in the org, including standard and custom objects.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="describe_object",
            description="Get field metadata for a Salesforce object — field names, types, and labels.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "Salesforce object API name, e.g. Opportunity",
                    }
                },
                "required": ["object_name"],
            },
        ),
        Tool(
            name="invoke_flow",
            description="Trigger an autolaunched Salesforce flow with input variables.",
            inputSchema={
                "type": "object",
                "properties": {
                    "flow_api_name": {"type": "string", "description": "The API name of the flow"},
                    "inputs": {
                        "type": "object",
                        "description": "Input variable name/value pairs for the flow",
                    },
                },
                "required": ["flow_api_name", "inputs"],
            },
        ),
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "query_records":
            result = tools.records.query_records(arguments["soql"])
        elif name == "get_record":
            result = tools.records.get_record(arguments["object_name"], arguments["record_id"])
        elif name == "create_record":
            result = tools.records.create_record(arguments["object_name"], arguments["fields"])
        elif name == "update_record":
            result = tools.records.update_record(arguments["object_name"], arguments["record_id"], arguments["fields"])
        elif name == "delete_record":
            result = tools.records.delete_record(arguments["object_name"], arguments["record_id"])
        elif name == "list_objects":
            result = tools.schema.list_objects()
        elif name == "describe_object":
            result = tools.schema.describe_object(arguments["object_name"])
        elif name == "invoke_flow":
            result = tools.flows.invoke_flow(arguments["flow_api_name"], arguments["inputs"])
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Salesforce MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP/SSE transport")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP/SSE transport")
    return parser.parse_args(argv)


def run_http_server(host: str, port: int) -> None:
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route
    import uvicorn

    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())

    starlette_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )

    uvicorn.run(starlette_app, host=host, port=port)


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    args = _parse_args()
    if args.transport == "http":
        run_http_server(args.host, args.port)
    else:
        asyncio.run(main())

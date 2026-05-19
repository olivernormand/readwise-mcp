"""Lightweight CLI for exercising Readwise MCP tools locally.

Calls tools through an in-memory FastMCP client, so it tests the real tool
dispatch path (argument parsing, validation, serialization) rather than the
raw functions.

Usage:
    python -m readwise_mcp.cli --list
    python -m readwise_mcp.cli <tool> [key=value ...]

Argument values are parsed as JSON when possible, otherwise treated as plain
strings:
    python -m readwise_mcp.cli verify_token
    python -m readwise_mcp.cli get_recent_highlights hours=24
    python -m readwise_mcp.cli export_highlights 'book_ids=[123,456]'
    python -m readwise_mcp.cli search_highlights "vector_search_term=deep work"

Quote any value containing spaces, brackets, or braces so the shell does not
expand it (e.g. 'book_ids=[1,2]', "vector_search_term=deep work").

ACCESS_TOKEN is read from the environment, or from a .env file in the current
directory if present.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from fastmcp import Client

from readwise_mcp.server import mcp


def load_env() -> None:
    """Load KEY=VALUE pairs from a local .env file into the environment."""
    env_path = Path(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def parse_value(raw: str):
    """Parse an argument value as JSON, falling back to a plain string."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


async def list_tools() -> None:
    tools = await mcp.get_tools()
    for name, tool in sorted(tools.items()):
        description = (tool.description or "").strip()
        summary = description.splitlines()[0] if description else ""
        print(f"  {name:<24} {summary}")


async def call(tool_name: str, args: dict) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, args)
    # The text content block holds the tool's JSON return verbatim; result.data
    # mis-deserializes list[dict] returns, so parse the text directly.
    if result.content and getattr(result.content[0], "text", None) is not None:
        try:
            output = json.loads(result.content[0].text)
        except json.JSONDecodeError:
            output = result.content[0].text
    else:
        output = result.structured_content if result.structured_content is not None else result.data
    print(json.dumps(output, indent=2, default=str))


def main() -> None:
    load_env()
    argv = sys.argv[1:]
    if not argv or argv[0] in ("--list", "-l", "--help", "-h"):
        print(__doc__)
        print("Available tools:")
        asyncio.run(list_tools())
        return

    tool_name = argv[0]
    args = {}
    for item in argv[1:]:
        if "=" not in item:
            sys.exit(f"Invalid argument '{item}': expected key=value")
        key, _, raw = item.partition("=")
        args[key] = parse_value(raw)

    try:
        asyncio.run(call(tool_name, args))
    except Exception as e:
        sys.exit(f"Error calling '{tool_name}': {e}")


if __name__ == "__main__":
    main()

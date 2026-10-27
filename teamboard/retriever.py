"""Client for the BrowseComp-Plus retrieval server (searcher/mcp_server.py). One instance is shared by all agents.

Every call opens its own short MCP session: with one long-lived session, a single transport error (e.g. a
connect timeout) disconnects the fastmcp 2.9.2 client for good and every later search of the run fails.
"""

import json

from fastmcp import Client

from teamboard.llm import ToolSpec


class Retriever:
    def __init__(self, url: str):
        self.url = url
        self.tool_specs: list[ToolSpec] = []

    async def load_tool_specs(self) -> None:
        # The server defines `search` (and `get_document` if started with --get-document), so the agents
        # see exactly the same tool descriptions and schemas as the BrowseComp-Plus baselines.
        async with Client(self.url) as client:
            tools = await client.list_tools()
        self.tool_specs = [ToolSpec(tool.name, tool.description, tool.inputSchema) for tool in tools]

    async def call(self, name: str, args: dict) -> tuple[str, list[str]]:
        """Returns the tool output shown to the agent and the docids it contains."""
        async with Client(self.url) as client:
            result = await client.call_tool_mcp(name, args)
        text = "\n".join(block.text for block in result.content)
        if result.isError:
            raise RuntimeError(text)
        return text or "[]", extract_docids(text)


def extract_docids(text: str) -> list[str]:
    # fastmcp 2.9.2 sends a JSON list for several hits, a bare object for a single hit and nothing for no hit.
    if not text:
        return []
    data = json.loads(text)
    items = data if isinstance(data, list) else [data]
    return [str(item["docid"]) for item in items if isinstance(item, dict) and "docid" in item]

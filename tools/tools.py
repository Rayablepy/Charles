import asyncio
from tools.rag import query_data
from tools.todo import todo_tool_list
from tools.web import get_web_tools
web_tools=asyncio.run(get_web_tools())
tool_list = [
    query_data,
    *todo_tool_list,
    *web_tools,
]

import asyncio
from tools.rag import query_data
from tools.todo import todo_tool_list

tool_list = [
    query_data,
    *todo_tool_list,
]

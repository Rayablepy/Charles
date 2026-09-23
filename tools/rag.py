from langchain_core.tools import tool
from memory.vectorstore import get_retriever

@tool
async def query_data(query: str) -> str:
    """Query a local RAG database for information matching the query

    Args:
        query (str): The query string to search for in the database

    Returns:
        str: The matching results from the database
    """
    results = await get_retriever().ainvoke(query)
    lines = []
    for doc in results:
        source = doc.metadata.get("source", "unknown")
        content = doc.page_content[:2000]
        lines.append(f"[source: {source}]\n{content}")
    return "Results:\n\n" + "\n".join(lines)

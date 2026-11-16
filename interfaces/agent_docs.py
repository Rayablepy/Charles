import asyncio
from datetime import datetime, timezone
from pathlib import Path

import click
from langgraph.store.sqlite.aio import AsyncSqliteStore
from config.settings import DB_PATH

NAMESPACE = ("Charles", "longterm")

DOCS = {
    "agents": ("/AGENTS.md", "AGENTS.md"),
    "userinfo": ("/USERINFO.md", "USERINFO.md"),
    "system-prompt": ("/SYSTEM_PROMPT.md", "SYSTEM_PROMPT.md"),
}

async def with_store():
    store_cm = AsyncSqliteStore.from_conn_string(str(DB_PATH))
    store = await store_cm.__aenter__()
    await store.setup()
    return store_cm, store

async def read_document(name: str) -> dict | None:
    path, _ = DOCS[name]
    store_cm, store = await with_store()
    try:
        item = await store.aget(NAMESPACE, path)
    finally:
        await store_cm.__aexit__(None, None, None)
    if item is None:
        return None
    return dict(item.value)


async def write_document(name: str, content: str) -> str:
    path, label = DOCS[name]
    store_cm, store = await with_store()
    try:
        item = await store.aget(NAMESPACE, path)
        time = datetime.now(timezone.utc).isoformat()
        value = dict(item.value) if item is not None else {}
        value.setdefault("encoding", "utf-8")
        value.setdefault("created_at", time)
        value["content"] = content
        value["modified_at"] = time
        await store.aput(NAMESPACE, path, value)
    finally:
        await store_cm.__aexit__(None, None, None)
    return label


async def list_documents() -> list[dict]:
    store_cm, store = await with_store()
    try:
        items = []
        for document, (path, label) in DOCS.items():
            item = await store.aget(NAMESPACE, path)
            items.append(
                {
                    "document": document,
                    "label": label,
                    "modified_at": (
                        item.value.get("modified_at", "")
                        if item is not None
                        else ""
                    ),
                }
            )
        return items
    finally:
        await store_cm.__aexit__(None, None, None)


@click.group()
def main():
    """Read and modify Charles agent docs."""


@main.command("list")
def list_command():
    """List the three agent documents."""
    for item in asyncio.run(list_documents()):
        status = item["modified_at"] or "missing"
        click.echo(f"{item['document']}\t{item['label']}\t{status}")


@main.command("read")
@click.argument("document")
def read_command(document: str):
    """Print one document to stdout."""
    data = asyncio.run(read_document(document))
    if data is None:
        raise click.ClickException(f"{document} does not exist")
    click.echo(data.get("content", ""))


@main.command("write")
@click.argument("document")
@click.option(
    "--file",
    "source",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Read content from a file instead of stdin.",
)
def write_command(document: str, source: Path | None):
    """Replace one document from a file or stdin."""
    content = (
        source.read_text(encoding="utf-8")
        if source is not None
        else click.get_text_stream("stdin").read()
    )
    label = asyncio.run(write_document(document, content))
    click.echo(f"Updated {label}")


if __name__ == "__main__":
    main()

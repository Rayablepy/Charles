
from database.db import conn
from langchain_core.tools import tool
import time
@tool
def add_item(name:str, information:str):
    """Add a new item/task to execute to a todo list.
    Args:
        name (str): The name of the item/task.
        information (str): The description of the item/task.
    Returns:
        str: The name of the item added at the time of execution.
    """
    cursor = conn.cursor()
    timestamp=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    cursor.execute(
        "INSERT INTO TodoList (name, information, timestamp) VALUES (?, ?, ?)",
        (name, information,timestamp)
    )
    conn.commit()
    return f"Item {name} added at {timestamp}"

@tool
def alter_item_name(name:str, new_name:str):
    """Alter the name of an item/task in the todo list.
    Args:
        name (str): The name of the item/task.
        new_name (str): The new name of the item/task.
    Returns:
        str: The name of the item changed and its new name.
    """
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE TodoList SET name = ? WHERE name = ?",
        (new_name, name)
    )
    conn.commit()
    return f"Item {name} changed to {new_name}"
@tool
def alter_item_description(name:str, new_description:str):
    """Alter the description of an item/task in the todo list.
    Args:
        name (str): The name of the item/task.
        new_description (str): The new description of the item/task.
    Returns:
        str: The name of the item changed and its new description.
    """
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE TodoList SET information = ? WHERE name = ?",
        (new_description, name)
    )
    conn.commit()
    return f"Item {name}'s description changed to {new_description}"

@tool
def alter_item_status(name:str, complete:int):
    """Alter the status of an item/task in the todo list.
    Args:
        name (str): The name of the item/task.
        complete (int): The new status of the item/task. 0 represents incomplete, 1 represents complete. IT CAN ONLY BE 0 OR 1.
    Returns:
        str: The name of the item changed and its new status.
    """
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE TodoList SET complete = ? WHERE name = ?",
        (complete, name)
    )
    conn.commit()
    status = "complete" if complete == 1 else "incomplete"
    return f"Item {name}'s status changed to {status}"

@tool
def delete_item(name:str):
    """Delete an item/task from the todo list.
    Args:
        name (str): The name of the item/task.
    Returns:
        str: The name of the item deleted.
    """
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM TodoList WHERE name = ?",
        (name,)
    )
    conn.commit()
    return f"Item {name} deleted"
@tool
def delete_all_items():
    """Delete all items from the todo list.ONLY USE IF THE USER EXPLICITLY REQUESTS FOR IT.
        DO NOT USE THIS TOOL WITHOUT EXPLICIT PERMISSION FROM THE USER
        Returns:
            str: Confirmation message of the deletion.
        """
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM TodoList"
    )
    conn.commit()
    return "All items deleted"

@tool
def read_item(name:str):
    """Read an item/task from the todo list.
    Args:
        name (str): The name of the item/task.
    Returns:
        str: The name,description, time created and status of the item.
        """
    cursor=conn.cursor()
    cursor.execute(
        "SELECT * FROM TodoList WHERE name = ?",
        (name,)
    )
    row = cursor.fetchone()
    if not row:
        return f"Item '{name}' not found"
    item_id, item_name, information, timestamp, complete = row
    return (
        f"ID: {item_id} "
        f"Name: {item_name}"
        f"Description: {information} "
        f"Created: {timestamp}"
        f"Status: {'complete' if complete == 1 else 'incomplete'}"
    )

@tool
def read_all_items():
    """Read all the items and tasks in the todo list. DO NOT use this unless needed to
    find the names of all tasks for future operations or if the user explicitly requests it.
    Returns:
        str: A newline-separated list of all items and tasks and their metadata."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM TodoList"
    )
    rows = cursor.fetchall()
    if not rows:
        return "No items in the todo list"
    lines = []
    for item_id, item_name, information, timestamp, complete in rows:
        lines.append(
            f"ID: {item_id} "
            f"Name: {item_name}"
            f"Description: {information} "
            f"Created: {timestamp}"
            f"Status: {'complete' if complete == 1 else 'incomplete'}"
        )
    return "\n".join(lines)
todo_tool_list=[add_item, alter_item_name, alter_item_description, alter_item_status, delete_item, read_item, read_all_items]

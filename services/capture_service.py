from database import (
    add_entry,
    delete_entry,
    get_entries,
    update_entry_completed,
)


def create_entry(content: str, entry_type: str):
    add_entry(content, entry_type)


def fetch_entries():
    return get_entries()


def toggle_entry(entry_id: int, completed: bool):
    new_completed = not completed
    update_entry_completed(entry_id, int(new_completed))


def remove_entry(entry_id: int):
    delete_entry(entry_id)
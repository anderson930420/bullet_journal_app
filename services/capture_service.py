from database import (
    add_entry,
    delete_entry,
    get_entries,
    get_future_entries,
    get_monthly_entries,
    migrate_entry,
    update_entry_completed,
)


def create_entry(content: str, entry_type: str):
    add_entry(content, entry_type)


def fetch_entries():
    return get_entries()


def fetch_future_entries():
    return get_future_entries()


def fetch_monthly_entries():
    return get_monthly_entries()


def toggle_entry(entry_id: int, completed: bool):
    new_completed = not completed
    update_entry_completed(entry_id, int(new_completed))


def remove_entry(entry_id: int):
    delete_entry(entry_id)


def migrate_to_future(entry_id: int):
    migrate_entry(entry_id, "future")


def migrate_to_monthly(entry_id: int):
    migrate_entry(entry_id, "monthly")


def migrate_to_today(entry_id: int):
    migrate_entry(entry_id, "today")

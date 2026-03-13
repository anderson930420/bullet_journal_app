from database import (
    add_entry,
    delete_entry,
    get_deleted_entries,
    get_entries,
    get_future_entries,
    get_monthly_entries,
    migrate_entry,
    permanently_delete_entry,
    restore_entry,
    update_entry_completed,
)


def create_entry(content: str, entry_type: str):
    add_entry(content, entry_type)


def create_monthly_entry(content: str, entry_type: str):
    add_entry(content, entry_type, "monthly")


def create_future_entry(content: str, entry_type: str):
    add_entry(content, entry_type, "future")


def fetch_entries():
    return get_entries()


def fetch_future_entries():
    return get_future_entries()


def fetch_monthly_entries():
    return get_monthly_entries()


def fetch_deleted_entries():
    return get_deleted_entries()


def toggle_entry(entry_id: int, completed: bool):
    new_completed = not completed
    update_entry_completed(entry_id, int(new_completed))


def remove_entry(entry_id: int):
    delete_entry(entry_id)


def restore_deleted_entry(entry_id: int):
    restore_entry(entry_id)


def permanently_remove_entry(entry_id: int):
    permanently_delete_entry(entry_id)


def migrate_to_future(entry_id: int):
    migrate_entry(entry_id, "future")


def migrate_to_monthly(entry_id: int):
    migrate_entry(entry_id, "monthly")


def migrate_to_today(entry_id: int):
    migrate_entry(entry_id, "today")

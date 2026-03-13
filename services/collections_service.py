from database import (
    add_collection,
    delete_collection,
    get_collection,
    get_collections,
    permanently_delete_collection,
    restore_collection,
    update_collection_order,
    update_collection,
)


def fetch_collections():
    return get_collections()


def fetch_collection(collection_id: int):
    return get_collection(collection_id)


def save_collection(collection_id: int | None, title: str, content: str):
    if collection_id is None:
        return add_collection(title, content)

    update_collection(collection_id, title, content)
    return collection_id


def remove_collection(collection_id: int):
    delete_collection(collection_id)


def restore_deleted_collection(collection_id: int):
    restore_collection(collection_id)


def permanently_remove_collection(collection_id: int):
    permanently_delete_collection(collection_id)


def reorder_collections(collection_ids: list[int]):
    update_collection_order(collection_ids)

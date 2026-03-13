from database import (
    add_collection,
    get_collection,
    get_collections,
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

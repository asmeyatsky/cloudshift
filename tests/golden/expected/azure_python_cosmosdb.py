from google.cloud import firestore

db = firestore.Client()
collection = db.collection("items")


def create_item(item):
    """Create an item in Firestore."""
    doc_id = item.get("id", None)
    if doc_id:
        collection.document(doc_id).set(item)
    else:
        collection.add(item)


def read_item(item_id, partition_key=None):
    """Read an item from Firestore."""
    doc = collection.document(item_id).get()
    return doc.to_dict() if doc.exists else None


def query_items(field, op, value):
    """Query items from Firestore."""
    return [doc.to_dict() for doc in collection.where(field, op, value).stream()]


def delete_item(item_id, partition_key=None):
    """Delete an item from Firestore."""
    collection.document(item_id).delete()

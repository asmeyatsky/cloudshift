"""Google Cloud Firestore operations — CRUD, queries, and transactions."""

from google.cloud import firestore
from config import GCP_PROJECT_ID, FIRESTORE_COLLECTION


def get_firestore_client():
    """Create a Google Cloud Firestore client."""
    return firestore.Client(project=GCP_PROJECT_ID)


def get_collection():
    """Get the Firestore collection reference."""
    client = get_firestore_client()
    return client.collection(FIRESTORE_COLLECTION)


def create_item(item):
    """Insert a new document into the Firestore collection."""
    collection = get_collection()
    doc_ref = collection.document(item.get("id"))
    doc_ref.set(item)
    return item


def read_item(item_id, partition_key=None):
    """Read a single document from Firestore by ID."""
    collection = get_collection()
    doc = collection.document(item_id).get()
    if doc.exists:
        return doc.to_dict()
    return None


def update_item(item_id, partition_key=None, updates=None):
    """Update an existing document in Firestore."""
    collection = get_collection()
    doc_ref = collection.document(item_id)
    doc_ref.update(updates or {})
    return doc_ref.get().to_dict()


def delete_item(item_id, partition_key=None):
    """Delete a document from Firestore."""
    collection = get_collection()
    collection.document(item_id).delete()


def query_items(field, operator, value):
    """Run a query against the Firestore collection."""
    collection = get_collection()
    results = collection.where(field, operator, value).stream()
    return [doc.to_dict() for doc in results]


def run_transaction(item_id, update_fn):
    """Execute a Firestore transaction."""
    client = get_firestore_client()
    doc_ref = client.collection(FIRESTORE_COLLECTION).document(item_id)

    @firestore.transactional
    def txn(transaction):
        snapshot = doc_ref.get(transaction=transaction)
        new_data = update_fn(snapshot.to_dict())
        transaction.update(doc_ref, new_data)
        return new_data

    return txn(client.transaction())

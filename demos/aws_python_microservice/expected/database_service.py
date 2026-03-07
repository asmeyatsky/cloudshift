"""Firestore operations for item management."""

import uuid
from datetime import datetime

from google.cloud import firestore

from config import FIRESTORE_COLLECTION


db = firestore.Client()
collection_ref = db.collection(FIRESTORE_COLLECTION)


def create_item(data):
    """Create a new item in Firestore."""
    item = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.utcnow().isoformat(),
        "status": "active",
        **data,
    }
    try:
        collection_ref.document(item["id"]).set(item)
        return item
    except Exception as e:
        raise RuntimeError(f"Failed to create item: {e}")


def get_item(item_id):
    """Retrieve an item by its document ID."""
    try:
        doc = collection_ref.document(item_id).get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        raise RuntimeError(f"Failed to get item {item_id}: {e}")


def update_item(item_id, updates):
    """Update specific fields of a document."""
    try:
        doc_ref = collection_ref.document(item_id)
        doc_ref.update(updates)
        updated_doc = doc_ref.get()
        return updated_doc.to_dict()
    except Exception as e:
        raise RuntimeError(f"Failed to update item {item_id}: {e}")


def delete_item(item_id):
    """Delete a document from Firestore."""
    try:
        collection_ref.document(item_id).delete()
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to delete item {item_id}: {e}")


def query_by_status(status, limit=25):
    """Query items by status, ordered by creation date descending."""
    try:
        query = (
            collection_ref
            .where("status", "==", status)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        raise RuntimeError(f"Failed to query items by status: {e}")


def batch_write_items(items):
    """Write multiple items in a batch operation."""
    try:
        batch = db.batch()
        for item in items:
            item.setdefault("id", str(uuid.uuid4()))
            item.setdefault("created_at", datetime.utcnow().isoformat())
            doc_ref = collection_ref.document(item["id"])
            batch.set(doc_ref, item)
        batch.commit()
        return True
    except Exception as e:
        raise RuntimeError(f"Batch write failed: {e}")


def scan_all(filter_expression=None):
    """Retrieve all documents with an optional status filter."""
    try:
        query = collection_ref
        if filter_expression:
            query = query.where("status", "==", filter_expression)
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        raise RuntimeError(f"Scan failed: {e}")

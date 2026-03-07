"""Main application entry point for the GCP microservice."""

import json
import logging

from flask import Flask, request, jsonify
from google.cloud import storage
from google.cloud import firestore

from config import GCP_PROJECT_ID, GCS_BUCKET_NAME, FIRESTORE_COLLECTION
from storage_service import upload_file, download_file, list_files, generate_presigned_url
from database_service import create_item, get_item, update_item, delete_item, query_by_status
from messaging_service import send_message, publish_notification
from secrets_service import get_secret

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize GCP clients for health checks
storage_client = storage.Client()
firestore_client = firestore.Client()


@app.route("/health", methods=["GET"])
def health_check():
    """Verify connectivity to all GCP services."""
    try:
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        bucket.reload()
        collection = firestore_client.collection(FIRESTORE_COLLECTION)
        collection.limit(1).get()
        return jsonify({"status": "healthy", "project": GCP_PROJECT_ID}), 200
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return jsonify({"status": "unhealthy", "error": str(e)}), 503


@app.route("/items", methods=["POST"])
def create():
    """Create a new item and send a notification."""
    data = request.get_json()
    item = create_item(data)
    send_message({"action": "item_created", "item_id": item["id"]})
    publish_notification("Item Created", {"id": item["id"]})
    return jsonify(item), 201


@app.route("/items/<item_id>", methods=["GET"])
def read(item_id):
    """Get an item by ID."""
    item = get_item(item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(item), 200


@app.route("/items/<item_id>", methods=["PUT"])
def update(item_id):
    """Update an existing item."""
    updates = request.get_json()
    item = update_item(item_id, updates)
    return jsonify(item), 200


@app.route("/items/<item_id>", methods=["DELETE"])
def delete(item_id):
    """Delete an item."""
    delete_item(item_id)
    return jsonify({"deleted": item_id}), 200


@app.route("/items/status/<status>", methods=["GET"])
def list_by_status(status):
    """Query items by status."""
    items = query_by_status(status)
    return jsonify(items), 200


@app.route("/files", methods=["POST"])
def upload():
    """Upload a file to Cloud Storage."""
    file = request.files["file"]
    uri = upload_file(file, file.filename, file.content_type)
    return jsonify({"uri": uri}), 201


@app.route("/files", methods=["GET"])
def list_uploaded_files():
    """List uploaded files."""
    files = list_files()
    return jsonify(files), 200


@app.route("/config/secret", methods=["GET"])
def read_secret():
    """Read a secret value (keys redacted in response)."""
    secret = get_secret()
    return jsonify({"keys": list(secret.keys())}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)

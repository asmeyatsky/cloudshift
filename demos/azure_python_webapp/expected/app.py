"""Main web application integrating GCS, Firestore, Pub/Sub, and Secret Manager."""

from flask import Flask, request, jsonify
from blob_service import upload_blob, download_blob, list_blobs, generate_signed_url
from cosmos_service import create_item, read_item, query_items, delete_item
from messaging_service import send_queue_message, publish_to_topic, receive_queue_messages
from keyvault_service import get_secret, set_secret, list_secrets
from config import APP_PORT, APP_DEBUG

app = Flask(__name__)


@app.route("/blobs", methods=["GET"])
def api_list_blobs():
    prefix = request.args.get("prefix")
    return jsonify(list_blobs(prefix=prefix))


@app.route("/blobs/<name>", methods=["PUT"])
def api_upload_blob(name):
    data = request.get_data()
    url = upload_blob(name, data, content_type=request.content_type)
    return jsonify({"url": url})


@app.route("/blobs/<name>/signed", methods=["GET"])
def api_blob_signed_url(name):
    url = generate_signed_url(name, expiry_hours=2)
    return jsonify({"signed_url": url})


@app.route("/items", methods=["POST"])
def api_create_item():
    item = request.get_json()
    result = create_item(item)
    return jsonify({"id": result["id"]}), 201


@app.route("/items/<item_id>", methods=["GET"])
def api_get_item(item_id):
    category = request.args.get("category", "default")
    item = read_item(item_id, partition_key=category)
    return jsonify(item)


@app.route("/items/search", methods=["GET"])
def api_search_items():
    category = request.args.get("category")
    results = query_items("category", "==", category)
    return jsonify(results)


@app.route("/messages", methods=["POST"])
def api_send_message():
    payload = request.get_json()
    send_queue_message(payload["body"], properties=payload.get("properties"))
    return jsonify({"status": "sent"}), 202


@app.route("/messages", methods=["GET"])
def api_receive_messages():
    messages = receive_queue_messages(max_count=5)
    return jsonify(messages)


@app.route("/notifications", methods=["POST"])
def api_publish_notification():
    payload = request.get_json()
    publish_to_topic(payload["body"], subject=payload.get("subject"))
    return jsonify({"status": "published"}), 202


@app.route("/secrets/<name>", methods=["GET"])
def api_get_secret(name):
    value = get_secret(name)
    return jsonify({"name": name, "value": value})


@app.route("/secrets", methods=["POST"])
def api_set_secret():
    payload = request.get_json()
    result = set_secret(payload["name"], payload["value"])
    return jsonify(result), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=APP_PORT, debug=APP_DEBUG)

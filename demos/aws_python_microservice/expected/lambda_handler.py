"""Cloud Function handler for processing Cloud Storage events and writing to Firestore."""

import json
import logging
from datetime import datetime

from google.cloud import firestore
from google.cloud import storage
from google.cloud import pubsub_v1

from config import GCP_PROJECT_ID, FIRESTORE_COLLECTION, PUBSUB_NOTIFICATION_TOPIC

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

db = firestore.Client()
collection_ref = db.collection(FIRESTORE_COLLECTION)
storage_client = storage.Client()
publisher = pubsub_v1.PublisherClient()
notification_topic = publisher.topic_path(GCP_PROJECT_ID, PUBSUB_NOTIFICATION_TOPIC)


def handler(event, context):
    """Process Cloud Storage event notifications triggered by object uploads."""
    logger.info("Received event: %s", json.dumps(event))

    bucket_name = event.get("bucket")
    file_name = event.get("name")
    size = int(event.get("size", 0))

    if not bucket_name or not file_name:
        logger.warning("Missing bucket or file name in event")
        return {"statusCode": 400, "body": "Missing event data"}

    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        blob.reload()
        content_type = blob.content_type or "unknown"

        item = {
            "id": f"{bucket_name}/{file_name}",
            "bucket": bucket_name,
            "key": file_name,
            "size": size,
            "content_type": content_type,
            "processed_at": datetime.utcnow().isoformat(),
            "status": "processed",
            "execution_id": context.event_id,
        }
        collection_ref.document(item["id"]).set(item)

        message_data = json.dumps({
            "bucket": bucket_name,
            "key": file_name,
            "status": "processed",
        }).encode("utf-8")
        publisher.publish(
            notification_topic,
            message_data,
            subject="File Processed",
        )
        logger.info("Processed gs://%s/%s", bucket_name, file_name)

    except Exception as e:
        logger.error("Error processing %s/%s: %s", bucket_name, file_name, e)
        raise

    return {
        "statusCode": 200,
        "body": json.dumps({"processed": 1}),
    }

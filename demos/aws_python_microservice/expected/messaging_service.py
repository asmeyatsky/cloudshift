"""Pub/Sub messaging operations."""

import json

from google.cloud import pubsub_v1
from google.api_core.exceptions import GoogleAPICallError

from config import (
    GCP_PROJECT_ID,
    PUBSUB_TOPIC,
    PUBSUB_SUBSCRIPTION,
    PUBSUB_NOTIFICATION_TOPIC,
    PUBSUB_DLQ_SUBSCRIPTION,
)


publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()

topic_path = publisher.topic_path(GCP_PROJECT_ID, PUBSUB_TOPIC)
subscription_path = subscriber.subscription_path(GCP_PROJECT_ID, PUBSUB_SUBSCRIPTION)
notification_topic_path = publisher.topic_path(GCP_PROJECT_ID, PUBSUB_NOTIFICATION_TOPIC)
dlq_subscription_path = subscriber.subscription_path(GCP_PROJECT_ID, PUBSUB_DLQ_SUBSCRIPTION)


def send_message(payload, delay_seconds=0):
    """Publish a message to the Pub/Sub topic."""
    try:
        data = json.dumps(payload).encode("utf-8")
        future = publisher.publish(topic_path, data)
        return future.result()
    except GoogleAPICallError as e:
        raise RuntimeError(f"Failed to publish Pub/Sub message: {e}")


def receive_messages(max_messages=10, wait_time=20):
    """Pull messages from the Pub/Sub subscription."""
    try:
        response = subscriber.pull(
            request={"subscription": subscription_path, "max_messages": max_messages},
            timeout=wait_time,
        )
        messages = []
        for msg in response.received_messages:
            messages.append({
                "id": msg.message.message_id,
                "body": json.loads(msg.message.data.decode("utf-8")),
                "ack_id": msg.ack_id,
            })
        return messages
    except GoogleAPICallError as e:
        raise RuntimeError(f"Failed to pull Pub/Sub messages: {e}")


def delete_message(ack_id):
    """Acknowledge a processed message."""
    try:
        subscriber.acknowledge(
            request={"subscription": subscription_path, "ack_ids": [ack_id]}
        )
        return True
    except GoogleAPICallError as e:
        raise RuntimeError(f"Failed to acknowledge Pub/Sub message: {e}")


def publish_notification(subject, message, attributes=None):
    """Publish a notification to the notification topic."""
    data = json.dumps(message).encode("utf-8") if isinstance(message, dict) else message.encode("utf-8")
    attrs = {"subject": subject}
    if attributes:
        attrs.update({k: str(v) for k, v in attributes.items()})
    try:
        future = publisher.publish(notification_topic_path, data, **attrs)
        return future.result()
    except GoogleAPICallError as e:
        raise RuntimeError(f"Failed to publish notification: {e}")


def get_dlq_messages(max_messages=10):
    """Retrieve messages from the dead letter subscription for inspection."""
    try:
        response = subscriber.pull(
            request={"subscription": dlq_subscription_path, "max_messages": max_messages},
        )
        return [msg.message for msg in response.received_messages]
    except GoogleAPICallError as e:
        raise RuntimeError(f"Failed to read DLQ: {e}")


def get_subscription_info():
    """Get subscription details including message backlog."""
    try:
        subscription = subscriber.get_subscription(
            request={"subscription": subscription_path}
        )
        return {"name": subscription.name, "topic": subscription.topic}
    except GoogleAPICallError as e:
        raise RuntimeError(f"Failed to get subscription info: {e}")

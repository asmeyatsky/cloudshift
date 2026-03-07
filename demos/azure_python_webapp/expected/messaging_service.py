"""Google Cloud Pub/Sub messaging — publish and subscribe to topics."""

from google.cloud import pubsub_v1
from config import GCP_PROJECT_ID, PUBSUB_QUEUE_TOPIC, PUBSUB_QUEUE_SUBSCRIPTION, PUBSUB_NOTIFICATION_TOPIC


def get_publisher():
    """Create a Google Cloud Pub/Sub publisher client."""
    return pubsub_v1.PublisherClient()


def get_subscriber():
    """Create a Google Cloud Pub/Sub subscriber client."""
    return pubsub_v1.SubscriberClient()


def send_queue_message(body, properties=None):
    """Publish a single message to the task queue Pub/Sub topic."""
    publisher = get_publisher()
    topic_path = publisher.topic_path(GCP_PROJECT_ID, PUBSUB_QUEUE_TOPIC)
    attrs = properties or {}
    future = publisher.publish(topic_path, body.encode("utf-8"), **attrs)
    return future.result()


def send_queue_batch(messages):
    """Publish a batch of messages to the task queue Pub/Sub topic."""
    publisher = get_publisher()
    topic_path = publisher.topic_path(GCP_PROJECT_ID, PUBSUB_QUEUE_TOPIC)
    futures = []
    for msg_body in messages:
        future = publisher.publish(topic_path, msg_body.encode("utf-8"))
        futures.append(future)
    return [f.result() for f in futures]


def receive_queue_messages(max_count=10, timeout=5):
    """Pull messages from the task queue Pub/Sub subscription."""
    subscriber = get_subscriber()
    subscription_path = subscriber.subscription_path(GCP_PROJECT_ID, PUBSUB_QUEUE_SUBSCRIPTION)
    response = subscriber.pull(
        request={"subscription": subscription_path, "max_messages": max_count},
        timeout=timeout,
    )
    results = []
    ack_ids = []
    for msg in response.received_messages:
        results.append({"body": msg.message.data.decode("utf-8"), "id": msg.message.message_id})
        ack_ids.append(msg.ack_id)
    if ack_ids:
        subscriber.acknowledge(request={"subscription": subscription_path, "ack_ids": ack_ids})
    return results


def publish_to_topic(body, subject=None):
    """Publish a message to the notifications Pub/Sub topic."""
    publisher = get_publisher()
    topic_path = publisher.topic_path(GCP_PROJECT_ID, PUBSUB_NOTIFICATION_TOPIC)
    attrs = {}
    if subject:
        attrs["subject"] = subject
    future = publisher.publish(topic_path, body.encode("utf-8"), **attrs)
    return future.result()

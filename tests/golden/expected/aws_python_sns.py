from google.cloud import pubsub_v1
import json

publisher = pubsub_v1.PublisherClient()
TOPIC_PATH = "projects/my-project/topics/notifications"


def publish_notification(subject, message):
    """Publish a notification to Pub/Sub topic."""
    publisher.publish(
        TOPIC_PATH,
        data=json.dumps(message).encode("utf-8"),
        subject=subject,
    )


def publish_sms(phone_number, message):
    """Send an SMS via Pub/Sub (requires SMS integration)."""
    publisher.publish(
        TOPIC_PATH,
        data=message.encode("utf-8"),
        phone_number=phone_number,
    )

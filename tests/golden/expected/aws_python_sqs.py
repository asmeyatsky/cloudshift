from google.cloud import pubsub_v1
import json

publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()
TOPIC_PATH = "projects/my-project/topics/my-queue"
SUBSCRIPTION_PATH = "projects/my-project/subscriptions/my-queue-sub"


def send_message(message_body):
    """Send a message to Pub/Sub topic."""
    publisher.publish(
        TOPIC_PATH,
        data=json.dumps(message_body).encode("utf-8"),
    )


def receive_messages(max_messages=10):
    """Receive messages from Pub/Sub subscription."""
    response = subscriber.pull(
        subscription=SUBSCRIPTION_PATH,
        max_messages=max_messages,
    )
    messages = [json.loads(m.message.data.decode("utf-8")) for m in response.received_messages]
    return messages


def delete_message(ack_id):
    """Acknowledge a message in Pub/Sub."""
    subscriber.acknowledge(
        subscription=SUBSCRIPTION_PATH,
        ack_ids=[ack_id],
    )

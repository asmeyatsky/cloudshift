from google.cloud import pubsub_v1

publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()
topic_path = "projects/my-project/topics/my-queue"
subscription_path = "projects/my-project/subscriptions/my-queue-sub"


def send_message(body):
    """Send a message to Pub/Sub topic."""
    publisher.publish(topic_path, data=body.encode("utf-8"))


def receive_messages(max_messages=10):
    """Receive messages from Pub/Sub subscription."""
    response = subscriber.pull(
        subscription=subscription_path,
        max_messages=max_messages,
    )
    results = []
    ack_ids = []
    for msg in response.received_messages:
        results.append(msg.message.data.decode("utf-8"))
        ack_ids.append(msg.ack_id)
    if ack_ids:
        subscriber.acknowledge(subscription=subscription_path, ack_ids=ack_ids)
    return results

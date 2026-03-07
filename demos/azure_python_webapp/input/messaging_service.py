"""Azure Service Bus messaging — send/receive queue messages and topic publishing."""

from azure.servicebus import ServiceBusClient, ServiceBusMessage
from config import (
    AZURE_SERVICEBUS_CONNECTION_STRING,
    AZURE_SERVICEBUS_QUEUE_NAME,
    AZURE_SERVICEBUS_TOPIC_NAME,
)


def get_servicebus_client():
    """Create an Azure ServiceBusClient from the connection string."""
    return ServiceBusClient.from_connection_string(AZURE_SERVICEBUS_CONNECTION_STRING)


def send_queue_message(body, properties=None):
    """Send a single message to an Azure Service Bus queue."""
    client = get_servicebus_client()
    with client:
        sender = client.get_queue_sender(queue_name=AZURE_SERVICEBUS_QUEUE_NAME)
        with sender:
            message = ServiceBusMessage(body)
            if properties:
                message.application_properties = properties
            sender.send_messages(message)


def send_queue_batch(messages):
    """Send a batch of messages to an Azure Service Bus queue."""
    client = get_servicebus_client()
    with client:
        sender = client.get_queue_sender(queue_name=AZURE_SERVICEBUS_QUEUE_NAME)
        with sender:
            batch = sender.create_message_batch()
            for msg_body in messages:
                batch.add_message(ServiceBusMessage(msg_body))
            sender.send_messages(batch)


def receive_queue_messages(max_count=10, timeout=5):
    """Receive messages from an Azure Service Bus queue."""
    client = get_servicebus_client()
    with client:
        receiver = client.get_queue_receiver(
            queue_name=AZURE_SERVICEBUS_QUEUE_NAME, max_wait_time=timeout
        )
        with receiver:
            messages = receiver.receive_messages(max_message_count=max_count)
            results = []
            for msg in messages:
                results.append({"body": str(msg), "id": msg.message_id})
                receiver.complete_message(msg)
            return results


def publish_to_topic(body, subject=None):
    """Publish a message to an Azure Service Bus topic."""
    client = get_servicebus_client()
    with client:
        sender = client.get_topic_sender(topic_name=AZURE_SERVICEBUS_TOPIC_NAME)
        with sender:
            message = ServiceBusMessage(body)
            if subject:
                message.subject = subject
            sender.send_messages(message)

from azure.servicebus import ServiceBusClient, ServiceBusMessage

connection_string = "Endpoint=sb://mynamespace.servicebus.windows.net/;SharedAccessKeyName=..."
queue_name = "my-queue"


def send_message(body):
    """Send a message to Azure Service Bus queue."""
    with ServiceBusClient.from_connection_string(connection_string) as client:
        with client.get_queue_sender(queue_name=queue_name) as sender:
            message = ServiceBusMessage(body)
            sender.send_messages(message)


def receive_messages(max_messages=10):
    """Receive messages from Azure Service Bus queue."""
    with ServiceBusClient.from_connection_string(connection_string) as client:
        with client.get_queue_receiver(queue_name=queue_name) as receiver:
            messages = receiver.receive_messages(max_message_count=max_messages, max_wait_time=5)
            results = []
            for msg in messages:
                results.append(str(msg))
                receiver.complete_message(msg)
            return results

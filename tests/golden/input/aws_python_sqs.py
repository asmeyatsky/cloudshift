import boto3
import json

sqs = boto3.client('sqs')
QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789/my-queue"


def send_message(message_body):
    """Send a message to SQS queue."""
    sqs.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps(message_body),
    )


def receive_messages(max_messages=10):
    """Receive messages from SQS queue."""
    response = sqs.receive_message(
        QueueUrl=QUEUE_URL,
        MaxNumberOfMessages=max_messages,
        WaitTimeSeconds=20,
    )
    messages = response.get('Messages', [])
    return [json.loads(m['Body']) for m in messages]


def delete_message(receipt_handle):
    """Delete a message from SQS queue."""
    sqs.delete_message(
        QueueUrl=QUEUE_URL,
        ReceiptHandle=receipt_handle,
    )

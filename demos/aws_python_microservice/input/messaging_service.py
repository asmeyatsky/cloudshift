"""SQS and SNS messaging operations."""

import json

import boto3
from botocore.exceptions import ClientError

from config import AWS_REGION, SQS_QUEUE_URL, SQS_DLQ_URL, SNS_TOPIC_ARN


sqs_client = boto3.client("sqs", region_name=AWS_REGION)
sns_client = boto3.client("sns", region_name=AWS_REGION)


def send_message(payload, delay_seconds=0):
    """Send a message to the SQS queue."""
    try:
        response = sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(payload),
            DelaySeconds=delay_seconds,
        )
        return response["MessageId"]
    except ClientError as e:
        raise RuntimeError(f"Failed to send SQS message: {e}")


def receive_messages(max_messages=10, wait_time=20):
    """Receive messages from the SQS queue using long polling."""
    try:
        response = sqs_client.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_time,
            AttributeNames=["All"],
        )
        messages = response.get("Messages", [])
        return [
            {
                "id": msg["MessageId"],
                "body": json.loads(msg["Body"]),
                "receipt_handle": msg["ReceiptHandle"],
            }
            for msg in messages
        ]
    except ClientError as e:
        raise RuntimeError(f"Failed to receive SQS messages: {e}")


def delete_message(receipt_handle):
    """Delete a processed message from the SQS queue."""
    try:
        sqs_client.delete_message(
            QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle
        )
        return True
    except ClientError as e:
        raise RuntimeError(f"Failed to delete SQS message: {e}")


def publish_notification(subject, message, attributes=None):
    """Publish a notification to the SNS topic."""
    params = {
        "TopicArn": SNS_TOPIC_ARN,
        "Subject": subject,
        "Message": json.dumps(message) if isinstance(message, dict) else message,
    }
    if attributes:
        params["MessageAttributes"] = {
            k: {"DataType": "String", "StringValue": str(v)}
            for k, v in attributes.items()
        }
    try:
        response = sns_client.publish(**params)
        return response["MessageId"]
    except ClientError as e:
        raise RuntimeError(f"Failed to publish SNS notification: {e}")


def get_dlq_messages(max_messages=10):
    """Retrieve messages from the dead letter queue for inspection."""
    try:
        response = sqs_client.receive_message(
            QueueUrl=SQS_DLQ_URL,
            MaxNumberOfMessages=max_messages,
            AttributeNames=["All"],
        )
        return response.get("Messages", [])
    except ClientError as e:
        raise RuntimeError(f"Failed to read DLQ: {e}")


def get_queue_attributes():
    """Get the approximate message count and other queue attributes."""
    try:
        response = sqs_client.get_queue_attributes(
            QueueUrl=SQS_QUEUE_URL,
            AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
        )
        return response["Attributes"]
    except ClientError as e:
        raise RuntimeError(f"Failed to get queue attributes: {e}")

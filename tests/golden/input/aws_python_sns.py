import boto3
import json

sns = boto3.client('sns')
TOPIC_ARN = "arn:aws:sns:us-east-1:123456789:notifications"


def publish_notification(subject, message):
    """Publish a notification to SNS topic."""
    sns.publish(
        TopicArn=TOPIC_ARN,
        Subject=subject,
        Message=json.dumps(message),
    )


def publish_sms(phone_number, message):
    """Send an SMS via SNS."""
    sns.publish(
        PhoneNumber=phone_number,
        Message=message,
    )

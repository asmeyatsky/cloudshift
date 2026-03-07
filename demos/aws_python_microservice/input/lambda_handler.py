"""AWS Lambda handler for processing S3 events and writing to DynamoDB."""

import json
import logging
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

from config import AWS_REGION, DYNAMODB_TABLE_NAME, SNS_TOPIC_ARN

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)
s3_client = boto3.client("s3", region_name=AWS_REGION)
sns_client = boto3.client("sns", region_name=AWS_REGION)


def handler(event, context):
    """Process S3 event notifications triggered by object uploads."""
    logger.info("Received event: %s", json.dumps(event))
    processed = 0

    for record in event.get("Records", []):
        event_name = record.get("eventName", "")
        if not event_name.startswith("ObjectCreated"):
            continue

        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        size = record["s3"]["object"].get("size", 0)

        try:
            metadata = s3_client.head_object(Bucket=bucket, Key=key)
            content_type = metadata.get("ContentType", "unknown")

            item = {
                "id": f"{bucket}/{key}",
                "bucket": bucket,
                "key": key,
                "size": size,
                "content_type": content_type,
                "processed_at": datetime.utcnow().isoformat(),
                "status": "processed",
                "lambda_request_id": context.aws_request_id,
            }
            table.put_item(Item=item)

            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject="File Processed",
                Message=json.dumps({
                    "bucket": bucket,
                    "key": key,
                    "status": "processed",
                }),
            )
            processed += 1
            logger.info("Processed s3://%s/%s", bucket, key)

        except ClientError as e:
            logger.error("Error processing %s/%s: %s", bucket, key, e)
            raise

    return {
        "statusCode": 200,
        "body": json.dumps({"processed": processed}),
    }

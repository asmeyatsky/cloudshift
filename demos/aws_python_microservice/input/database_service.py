"""DynamoDB operations for item management."""

import uuid
from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from config import AWS_REGION, DYNAMODB_TABLE_NAME, DYNAMODB_GSI_NAME


dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)


def create_item(data):
    """Create a new item in DynamoDB."""
    item = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.utcnow().isoformat(),
        "status": "active",
        **data,
    }
    try:
        table.put_item(Item=item)
        return item
    except ClientError as e:
        raise RuntimeError(f"Failed to create item: {e}")


def get_item(item_id):
    """Retrieve an item by its primary key."""
    try:
        response = table.get_item(Key={"id": item_id})
        return response.get("Item")
    except ClientError as e:
        raise RuntimeError(f"Failed to get item {item_id}: {e}")


def update_item(item_id, updates):
    """Update specific attributes of an item."""
    expression_parts = []
    values = {}
    names = {}
    for i, (key, value) in enumerate(updates.items()):
        expression_parts.append(f"#{key} = :val{i}")
        values[f":val{i}"] = value
        names[f"#{key}"] = key
    try:
        response = table.update_item(
            Key={"id": item_id},
            UpdateExpression="SET " + ", ".join(expression_parts),
            ExpressionAttributeValues=values,
            ExpressionAttributeNames=names,
            ReturnValues="ALL_NEW",
        )
        return response["Attributes"]
    except ClientError as e:
        raise RuntimeError(f"Failed to update item {item_id}: {e}")


def delete_item(item_id):
    """Delete an item from DynamoDB."""
    try:
        table.delete_item(Key={"id": item_id})
        return True
    except ClientError as e:
        raise RuntimeError(f"Failed to delete item {item_id}: {e}")


def query_by_status(status, limit=25):
    """Query items by status using the GSI."""
    try:
        response = table.query(
            IndexName=DYNAMODB_GSI_NAME,
            KeyConditionExpression=Key("status").eq(status),
            Limit=limit,
            ScanIndexForward=False,
        )
        return response["Items"]
    except ClientError as e:
        raise RuntimeError(f"Failed to query items by status: {e}")


def batch_write_items(items):
    """Write multiple items in a batch operation."""
    try:
        with table.batch_writer() as batch:
            for item in items:
                item.setdefault("id", str(uuid.uuid4()))
                item.setdefault("created_at", datetime.utcnow().isoformat())
                batch.put_item(Item=item)
        return True
    except ClientError as e:
        raise RuntimeError(f"Batch write failed: {e}")


def scan_all(filter_expression=None):
    """Scan the entire table with an optional filter."""
    params = {}
    if filter_expression:
        params["FilterExpression"] = Attr("status").eq(filter_expression)
    items = []
    try:
        response = table.scan(**params)
        items.extend(response["Items"])
        while "LastEvaluatedKey" in response:
            params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            response = table.scan(**params)
            items.extend(response["Items"])
        return items
    except ClientError as e:
        raise RuntimeError(f"Scan failed: {e}")

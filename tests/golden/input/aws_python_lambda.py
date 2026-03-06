import json
import boto3

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('events')


def handler(event, context):
    """AWS Lambda handler for processing S3 events."""
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        response = s3.get_object(Bucket=bucket, Key=key)
        data = json.loads(response['Body'].read())

        table.put_item(Item={
            'id': data['id'],
            'source': f"s3://{bucket}/{key}",
            'payload': json.dumps(data),
        })

    return {
        'statusCode': 200,
        'body': json.dumps({'processed': len(event['Records'])})
    }

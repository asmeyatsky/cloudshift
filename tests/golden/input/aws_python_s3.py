import boto3
from botocore.config import Config

config = Config(region_name='us-east-1')
s3 = boto3.client('s3', config=config)


def upload_file(bucket, key, data):
    """Upload data to S3."""
    s3.put_object(Bucket=bucket, Key=key, Body=data)


def download_file(bucket, key):
    """Download file from S3."""
    response = s3.get_object(Bucket=bucket, Key=key)
    return response['Body'].read()


def list_files(bucket, prefix=""):
    """List files in S3 bucket."""
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    return [obj['Key'] for obj in response.get('Contents', [])]


def delete_file(bucket, key):
    """Delete file from S3."""
    s3.delete_object(Bucket=bucket, Key=key)

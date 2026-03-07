"""S3 storage operations for file management."""

import boto3
from botocore.exceptions import ClientError

from config import AWS_REGION, S3_BUCKET_NAME, S3_UPLOAD_PREFIX, S3_PRESIGNED_URL_EXPIRY


s3_client = boto3.client("s3", region_name=AWS_REGION)
s3_resource = boto3.resource("s3", region_name=AWS_REGION)


def upload_file(file_obj, filename, content_type="application/octet-stream"):
    """Upload a file to S3 with the given key."""
    key = f"{S3_UPLOAD_PREFIX}{filename}"
    try:
        s3_client.upload_fileobj(
            file_obj,
            S3_BUCKET_NAME,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return f"s3://{S3_BUCKET_NAME}/{key}"
    except ClientError as e:
        raise RuntimeError(f"S3 upload failed: {e}")


def download_file(key):
    """Download a file from S3 and return its body."""
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=key)
        return response["Body"].read()
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return None
        raise


def list_files(prefix=S3_UPLOAD_PREFIX):
    """List all objects under a prefix in the S3 bucket."""
    try:
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix)
        return [
            {"key": obj["Key"], "size": obj["Size"], "modified": obj["LastModified"]}
            for obj in response.get("Contents", [])
        ]
    except ClientError as e:
        raise RuntimeError(f"Failed to list S3 objects: {e}")


def delete_file(key):
    """Delete an object from S3."""
    try:
        s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=key)
        return True
    except ClientError as e:
        raise RuntimeError(f"Failed to delete S3 object {key}: {e}")


def generate_presigned_url(key, expiration=S3_PRESIGNED_URL_EXPIRY):
    """Generate a presigned URL for temporary access to an S3 object."""
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET_NAME, "Key": key},
            ExpiresIn=expiration,
        )
        return url
    except ClientError as e:
        raise RuntimeError(f"Failed to generate presigned URL: {e}")


def copy_file(source_key, dest_key):
    """Copy an object within the same S3 bucket."""
    copy_source = {"Bucket": S3_BUCKET_NAME, "Key": source_key}
    try:
        s3_client.copy_object(
            CopySource=copy_source, Bucket=S3_BUCKET_NAME, Key=dest_key
        )
        return True
    except ClientError as e:
        raise RuntimeError(f"Failed to copy S3 object: {e}")

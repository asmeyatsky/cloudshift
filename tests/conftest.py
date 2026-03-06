import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "golden"
INPUT_DIR = FIXTURES_DIR / "input"
EXPECTED_DIR = FIXTURES_DIR / "expected"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def input_dir():
    return INPUT_DIR


@pytest.fixture
def expected_dir():
    return EXPECTED_DIR


@pytest.fixture
def sample_boto3_source():
    return '''import boto3

s3 = boto3.client('s3')

def upload_file(bucket, key, data):
    s3.put_object(Bucket=bucket, Key=key, Body=data)

def download_file(bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    return response['Body'].read()

def list_files(bucket, prefix=""):
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    return [obj['Key'] for obj in response.get('Contents', [])]

def delete_file(bucket, key):
    s3.delete_object(Bucket=bucket, Key=key)
'''


@pytest.fixture
def sample_aws_sdk_ts_source():
    return '''import { S3Client, PutObjectCommand, GetObjectCommand } from "@aws-sdk/client-s3";

const client = new S3Client({ region: "us-east-1" });

export async function uploadFile(bucket: string, key: string, body: Buffer): Promise<void> {
    await client.send(new PutObjectCommand({ Bucket: bucket, Key: key, Body: body }));
}

export async function downloadFile(bucket: string, key: string): Promise<Buffer> {
    const response = await client.send(new GetObjectCommand({ Bucket: bucket, Key: key }));
    return Buffer.from(await response.Body!.transformToByteArray());
}
'''


@pytest.fixture
def sample_terraform_source():
    return '''provider "aws" {
  region = "us-east-1"
}

resource "aws_s3_bucket" "data_bucket" {
  bucket = "my-app-data"
}

resource "aws_dynamodb_table" "users" {
  name     = "users"
  hash_key = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

resource "aws_lambda_function" "processor" {
  function_name = "data-processor"
  runtime       = "python3.13"
  handler       = "main.handler"
  filename      = "lambda.zip"
}
'''


@pytest.fixture
def sample_gcp_python_expected():
    return '''from google.cloud import storage

client = storage.Client()

def upload_file(bucket_name, key, data):
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(key)
    blob.upload_from_string(data)

def download_file(bucket_name, key):
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(key)
    return blob.download_as_bytes()

def list_files(bucket_name, prefix=""):
    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)
    return [blob.name for blob in blobs]

def delete_file(bucket_name, key):
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(key)
    blob.delete()
'''

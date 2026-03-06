"""Integration test for full scan flow."""
import pytest
from pathlib import Path


@pytest.fixture
def aws_python_project(tmp_path):
    """Create a temporary AWS Python project."""
    (tmp_path / "app.py").write_text("""
import boto3
import json

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('events')

def process_event(event):
    bucket = event['bucket']
    key = event['key']
    response = s3.get_object(Bucket=bucket, Key=key)
    data = json.loads(response['Body'].read())
    table.put_item(Item={'id': data['id'], 'data': json.dumps(data)})
""")
    (tmp_path / "config.py").write_text("""
import os

AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
BUCKET_NAME = os.environ.get('S3_BUCKET', 'my-bucket')
""")
    return tmp_path


def test_scan_detects_aws_services(aws_python_project):
    """Test that scanning detects AWS services in Python code."""
    from cloudshift.cloudshift_core import py_walk_directory, py_parse_file, py_detect_services

    files = py_walk_directory(str(aws_python_project))
    assert len(files) >= 2

    all_detections = []
    for f in files:
        ast = py_parse_file(f)
        detections = py_detect_services(ast.nodes)
        all_detections.extend(detections)

    services = {d.service for d in all_detections}
    assert "sdk" in services or "s3" in services


def test_full_scan_to_manifest(aws_python_project):
    """Test full scan -> manifest generation."""
    from cloudshift.cloudshift_core import (
        py_walk_directory, py_parse_file, py_detect_services,
        py_create_manifest, PyManifestEntry
    )

    manifest = py_create_manifest("test-project", "aws", "gcp")
    files = py_walk_directory(str(aws_python_project))

    for f in files:
        ast = py_parse_file(f)
        detections = py_detect_services(ast.nodes)
        for detection in detections:
            entry = PyManifestEntry(
                file_path=f,
                construct_type=detection.construct_type,
                source_service=detection.service,
                target_service="",
                source_text="",
            )
            manifest.add_entry(entry)

    assert manifest.total_files > 0
    assert manifest.total_constructs > 0

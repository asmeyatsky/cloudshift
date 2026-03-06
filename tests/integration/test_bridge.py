"""Integration tests for the Rust-Python bridge via PyO3."""
import pytest


def test_import_cloudshift_core():
    from cloudshift import cloudshift_core
    assert cloudshift_core is not None


def test_parse_python_source():
    from cloudshift.cloudshift_core import py_parse_source

    source = """import boto3
s3 = boto3.client('s3')
"""
    ast = py_parse_source(source, "python", "test.py")
    assert ast.language == "python"
    assert ast.file_path == "test.py"
    assert len(ast.nodes) > 0

    imports = [n for n in ast.nodes if n.node_type == "import"]
    assert len(imports) >= 1


def test_parse_typescript_source():
    from cloudshift.cloudshift_core import py_parse_source

    source = '''import { S3Client } from "@aws-sdk/client-s3";
const client = new S3Client({ region: "us-east-1" });
'''
    ast = py_parse_source(source, "typescript", "test.ts")
    assert ast.language == "typescript"
    assert len(ast.nodes) > 0


def test_parse_hcl_source():
    from cloudshift.cloudshift_core import py_parse_source

    source = '''resource "aws_s3_bucket" "my_bucket" {
  bucket = "my-bucket"
}
'''
    ast = py_parse_source(source, "hcl", "main.tf")
    assert ast.language == "hcl"
    assert len(ast.nodes) >= 1
    assert ast.nodes[0].node_type == "resource_block"


def test_parse_cloudformation_source():
    from cloudshift.cloudshift_core import py_parse_source

    source = '''{
  "AWSTemplateFormatVersion": "2010-09-09",
  "Resources": {
    "MyBucket": {
      "Type": "AWS::S3::Bucket",
      "Properties": { "BucketName": "my-bucket" }
    }
  }
}'''
    ast = py_parse_source(source, "cloudformation", "template.json")
    assert ast.language == "cloudformation"
    assert len(ast.nodes) >= 1


def test_detect_services():
    from cloudshift.cloudshift_core import py_parse_source, py_detect_services

    source = """import boto3
s3 = boto3.client('s3')
"""
    ast = py_parse_source(source, "python", "test.py")
    detections = py_detect_services(ast.nodes)
    assert len(detections) > 0

    providers = {d.provider for d in detections}
    assert "aws" in providers


def test_unified_diff():
    from cloudshift.cloudshift_core import py_unified_diff

    old_text = "import boto3\ns3 = boto3.client('s3')\n"
    new_text = "from google.cloud import storage\nclient = storage.Client()\n"
    diff = py_unified_diff(old_text, new_text, "test.py")
    assert "--- a/test.py" in diff
    assert "+++ b/test.py" in diff
    assert "-import boto3" in diff
    assert "+from google.cloud import storage" in diff


def test_create_manifest():
    from cloudshift.cloudshift_core import py_create_manifest

    manifest = py_create_manifest("test-project", "aws", "gcp")
    assert manifest.project_name == "test-project"
    assert manifest.source_provider == "aws"
    assert manifest.target_provider == "gcp"
    assert manifest.total_files == 0


def test_scan_residual_refs():
    from cloudshift.cloudshift_core import py_scan_residual_refs

    source = '''from google.cloud import storage
client = storage.Client()
arn = "arn:aws:s3:::my-bucket"
'''
    result = py_scan_residual_refs(source, "test.py")
    assert not result.is_valid
    assert len(result.issues) > 0

    clean_source = '''from google.cloud import storage
client = storage.Client()
bucket = client.bucket("my-bucket")
'''
    result = py_scan_residual_refs(clean_source, "test.py")
    assert result.is_valid


def test_walk_directory(tmp_path):
    from cloudshift.cloudshift_core import py_walk_directory

    (tmp_path / "app.py").write_text("import boto3")
    (tmp_path / "main.ts").write_text("import { S3Client } from '@aws-sdk/client-s3'")
    (tmp_path / "config.tf").write_text('resource "aws_s3_bucket" "b" {}')
    (tmp_path / "readme.md").write_text("# README")

    files = py_walk_directory(str(tmp_path))
    extensions = {f.split(".")[-1] for f in files}
    assert "py" in extensions
    assert "ts" in extensions
    assert "tf" in extensions
    assert "md" not in extensions


def test_load_patterns():
    from cloudshift.cloudshift_core import py_load_patterns

    count = py_load_patterns("patterns")
    assert count >= 50


def test_match_and_transform():
    from cloudshift.cloudshift_core import py_load_patterns, py_match_and_transform

    py_load_patterns("patterns")

    result = py_match_and_transform(
        node_type="client_init",
        node_name="boto3.client",
        node_text="boto3.client('s3')",
        provider="aws",
        service="s3",
        language="python",
        metadata={},
    )
    assert result is not None
    assert result.confidence > 0
    assert len(result.transformed_text) > 0

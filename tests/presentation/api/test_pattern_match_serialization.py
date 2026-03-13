"""Test Fix 5: PatternMatchResponse serializes with camelCase aliases."""

from cloudshift.presentation.api.schemas import (
    PatternMatchResponse,
    FileScanResultResponse,
)


def test_pattern_match_response_serializes_camel_case():
    """model_dump(by_alias=True) must produce camelCase keys for VS Code extension."""
    m = PatternMatchResponse(
        line=10,
        end_line=12,
        column=4,
        end_column=20,
        pattern_id="p-aws-s3",
        pattern_name="S3 Bucket",
        severity="WARNING",
        message="Detected S3 usage",
        source_provider="AWS",
        target_provider="GCP",
    )
    dumped = m.model_dump(by_alias=True)
    # Must have camelCase keys, not snake_case
    assert "patternId" in dumped
    assert "patternName" in dumped
    assert "endLine" in dumped
    assert "endColumn" in dumped
    assert "sourceProvider" in dumped
    assert "targetProvider" in dumped
    # Must NOT have snake_case keys
    assert "pattern_id" not in dumped
    assert "pattern_name" not in dumped
    assert "end_line" not in dumped
    assert "source_provider" not in dumped


def test_pattern_match_response_default_serialization_uses_alias():
    """serialize_by_alias=True means even model_dump() without by_alias uses aliases."""
    m = PatternMatchResponse(
        line=1,
        end_line=1,
        column=0,
        end_column=10,
        pattern_id="p1",
        pattern_name="test",
        severity="INFO",
        message="msg",
        source_provider="AWS",
        target_provider="GCP",
    )
    # Default model_dump should also use aliases because of serialize_by_alias=True
    dumped = m.model_dump()
    assert "patternId" in dumped
    assert "pattern_id" not in dumped


def test_pattern_match_response_json_serialization():
    """FastAPI uses model.model_dump(mode='json') for response; verify camelCase."""
    m = PatternMatchResponse(
        line=5,
        end_line=8,
        column=0,
        end_column=30,
        pattern_id="p-ec2",
        pattern_name="EC2 Instance",
        severity="ERROR",
        message="EC2 detected",
        source_provider="AWS",
        target_provider="GCP",
    )
    import json
    json_str = m.model_dump_json()
    parsed = json.loads(json_str)
    assert "patternId" in parsed
    assert "patternName" in parsed
    assert "endLine" in parsed
    assert "sourceProvider" in parsed
    assert parsed["patternId"] == "p-ec2"
    assert parsed["patternName"] == "EC2 Instance"


def test_file_scan_result_response_contains_camel_patterns():
    """FileScanResultResponse embeds PatternMatchResponse; verify nested camelCase."""
    pattern = PatternMatchResponse(
        line=1,
        end_line=2,
        column=0,
        end_column=10,
        pattern_id="p1",
        pattern_name="test",
        severity="INFO",
        message="msg",
        source_provider="AWS",
        target_provider="GCP",
    )
    result = FileScanResultResponse(file="main.py", patterns=[pattern])
    dumped = result.model_dump()
    assert len(dumped["patterns"]) == 1
    p = dumped["patterns"][0]
    assert "patternId" in p
    assert "patternName" in p
    assert "endLine" in p

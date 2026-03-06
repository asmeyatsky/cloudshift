use std::collections::HashMap;

use super::ast_types::*;

pub fn parse(source: &str, file_path: String) -> Result<FileAst, ParseError> {
    // CloudFormation can be JSON or YAML - try both
    let value: serde_json::Value = if source.trim_start().starts_with('{') {
        serde_json::from_str(source)
            .map_err(|e| ParseError::InvalidSource(format!("Invalid CFn JSON: {}", e)))?
    } else {
        serde_yaml::from_str(source)
            .map_err(|e| ParseError::InvalidSource(format!("Invalid CFn YAML: {}", e)))?
    };

    let mut nodes = Vec::new();

    // Extract Resources
    if let Some(resources) = value.get("Resources").and_then(|r| r.as_object()) {
        for (name, resource) in resources {
            let resource_type = resource
                .get("Type")
                .and_then(|t| t.as_str())
                .unwrap_or("Unknown")
                .to_string();

            let mut metadata = HashMap::new();
            metadata.insert("block_type".to_string(), "resource".to_string());
            metadata.insert("resource_type".to_string(), resource_type.clone());

            // Serialize the resource back to get text representation
            let text = serde_json::to_string_pretty(resource).unwrap_or_default();

            nodes.push(AstNode {
                node_type: NodeType::ResourceBlock,
                name: format!("{}.{}", resource_type, name),
                text,
                start_line: 0,
                end_line: 0,
                start_col: 0,
                end_col: 0,
                children: vec![],
                metadata,
            });
        }
    }

    // Extract Parameters as variable assignments
    if let Some(params) = value.get("Parameters").and_then(|p| p.as_object()) {
        for (name, param) in params {
            let text = serde_json::to_string_pretty(param).unwrap_or_default();
            let mut metadata = HashMap::new();
            metadata.insert("block_type".to_string(), "parameter".to_string());
            nodes.push(AstNode {
                node_type: NodeType::VariableAssignment,
                name: name.clone(),
                text,
                start_line: 0,
                end_line: 0,
                start_col: 0,
                end_col: 0,
                children: vec![],
                metadata,
            });
        }
    }

    // Extract Outputs
    if let Some(outputs) = value.get("Outputs").and_then(|o| o.as_object()) {
        for (name, output) in outputs {
            let text = serde_json::to_string_pretty(output).unwrap_or_default();
            let mut metadata = HashMap::new();
            metadata.insert("block_type".to_string(), "output".to_string());
            nodes.push(AstNode {
                node_type: NodeType::Other,
                name: name.clone(),
                text,
                start_line: 0,
                end_line: 0,
                start_col: 0,
                end_col: 0,
                children: vec![],
                metadata,
            });
        }
    }

    Ok(FileAst {
        file_path,
        language: Language::CloudFormation,
        nodes,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_cfn_json() {
        let source = r#"{
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                "MyBucket": {
                    "Type": "AWS::S3::Bucket",
                    "Properties": {
                        "BucketName": "my-bucket"
                    }
                },
                "MyTable": {
                    "Type": "AWS::DynamoDB::Table",
                    "Properties": {
                        "TableName": "my-table"
                    }
                }
            }
        }"#;
        let ast = parse(source, "template.json".into()).unwrap();
        assert_eq!(ast.language, Language::CloudFormation);
        assert_eq!(ast.nodes.len(), 2);
    }

    #[test]
    fn test_parse_cfn_yaml() {
        let source = r#"
AWSTemplateFormatVersion: '2010-09-09'
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: my-bucket
"#;
        let ast = parse(source, "template.yaml".into()).unwrap();
        assert_eq!(ast.nodes.len(), 1);
        assert!(ast.nodes[0].name.contains("AWS::S3::Bucket"));
    }
}

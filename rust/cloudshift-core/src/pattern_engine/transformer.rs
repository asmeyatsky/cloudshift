use std::collections::HashMap;

use super::catalogue::PatternRule;

#[derive(Debug, Clone)]
pub struct TransformResult {
    pub pattern_id: String,
    pub original_text: String,
    pub transformed_text: String,
    pub import_additions: Vec<String>,
    pub import_removals: Vec<String>,
    pub confidence: f64,
    pub metadata: HashMap<String, String>,
}

pub fn apply_rule(rule: &PatternRule, original_text: &str) -> TransformResult {
    let transformed = apply_template(&rule.transform.replacement_template, original_text, rule);

    let confidence = rule.base_confidence;

    let mut metadata = HashMap::new();
    metadata.insert("pattern_name".to_string(), rule.name.clone());
    metadata.insert(
        "source_service".to_string(),
        rule.source_service.clone(),
    );
    metadata.insert(
        "target_service".to_string(),
        rule.target_service.clone(),
    );

    TransformResult {
        pattern_id: rule.id.clone(),
        original_text: original_text.to_string(),
        transformed_text: transformed,
        import_additions: rule.transform.import_additions.clone(),
        import_removals: rule.transform.import_removals.clone(),
        confidence,
        metadata,
    }
}

fn apply_template(template: &str, original_text: &str, rule: &PatternRule) -> String {
    let mut result = template.to_string();

    // Replace {{original}} placeholder
    result = result.replace("{{original}}", original_text);

    // Replace {{service}} placeholders
    result = result.replace("{{source_service}}", &rule.source_service);
    result = result.replace("{{target_service}}", &rule.target_service);

    // Extract and replace parameter placeholders like {{param:bucket_name}}
    // by trying to find them in the original text
    let param_re = regex::Regex::new(r"\{\{param:(\w+)\}\}").unwrap();
    for cap in param_re.captures_iter(&result.clone()) {
        let full_match = &cap[0];
        let param_name = &cap[1];
        if let Some(value) = extract_param(original_text, param_name) {
            result = result.replace(full_match, &value);
        }
    }

    result
}

fn extract_param(text: &str, param_name: &str) -> Option<String> {
    // Try to find param_name = "value" or param_name = 'value' patterns
    let patterns = [
        format!("{}=\"", param_name),
        format!("{}='", param_name),
        format!("{} = \"", param_name),
        format!("{} = '", param_name),
        format!("{}=", param_name),
    ];

    for pattern in &patterns {
        if let Some(idx) = text.find(pattern.as_str()) {
            let start = idx + pattern.len();
            let rest = &text[start..];
            let quote = if pattern.ends_with('"') {
                '"'
            } else if pattern.ends_with('\'') {
                '\''
            } else {
                // No quote, find next comma or paren
                let end = rest
                    .find([',', ')', '}', '\n'])
                    .unwrap_or(rest.len());
                return Some(rest[..end].trim().to_string());
            };
            if let Some(end) = rest.find(quote) {
                return Some(rest[..end].to_string());
            }
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pattern_engine::catalogue::*;

    #[test]
    fn test_apply_simple_template() {
        let rule = PatternRule {
            id: "test".into(),
            name: "Test".into(),
            description: String::new(),
            source_provider: "aws".into(),
            target_provider: "gcp".into(),
            source_service: "s3".into(),
            target_service: "gcs".into(),
            language: "python".into(),
            construct_type: "client_init".into(),
            match_pattern: MatchPattern {
                imports: vec![],
                client_names: vec![],
                method_names: vec![],
                resource_types: vec![],
                text_patterns: vec![],
            },
            transform: TransformSpec {
                replacement_template: "storage.Client()".into(),
                import_additions: vec![],
                import_removals: vec![],
                notes: String::new(),
            },
            base_confidence: 0.90,
            tags: vec![],
            examples: vec![],
        };

        let result = apply_rule(&rule, "boto3.client('s3')");
        assert_eq!(result.transformed_text, "storage.Client()");
        assert_eq!(result.confidence, 0.90);
    }
}

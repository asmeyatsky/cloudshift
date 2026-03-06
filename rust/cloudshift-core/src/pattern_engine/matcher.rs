use super::catalogue::{PatternRule, RuleCatalogue};

pub struct MatchConstruct {
    pub node_type: String,
    pub node_name: String,
    pub node_text: String,
    pub provider: String,
    pub service: String,
    pub language: String,
    pub metadata: std::collections::HashMap<String, String>,
}

pub fn find_best_match<'a>(
    catalogue: &'a RuleCatalogue,
    construct: &MatchConstruct,
) -> Option<&'a PatternRule> {
    let candidates = get_candidates(catalogue, construct);

    candidates
        .into_iter()
        .filter_map(|rule| {
            let score = compute_match_score(rule, construct);
            if score > 0.0 {
                Some((rule, score))
            } else {
                None
            }
        })
        .max_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal))
        .map(|(rule, _)| rule)
}

fn get_candidates<'a>(
    catalogue: &'a RuleCatalogue,
    construct: &MatchConstruct,
) -> Vec<&'a PatternRule> {
    let mut candidates = Vec::new();

    // Filter by provider first
    if let Some(indices) = catalogue.by_provider.get(&construct.provider) {
        for &idx in indices {
            let rule = &catalogue.rules[idx];
            // Filter by language compatibility
            if rule.language == construct.language || rule.language == "any" {
                candidates.push(rule);
            }
        }
    }

    // If no provider-specific matches, try "any" provider rules
    if candidates.is_empty() {
        if let Some(indices) = catalogue.by_provider.get("any") {
            for &idx in indices {
                candidates.push(&catalogue.rules[idx]);
            }
        }
    }

    candidates
}

fn compute_match_score(rule: &PatternRule, construct: &MatchConstruct) -> f64 {
    let mut score = 0.0;
    let mut checks = 0;

    // Service match
    if rule.source_service == construct.service {
        score += 2.0;
    } else if !construct.service.is_empty() {
        return 0.0; // Service mismatch is a hard fail
    }
    checks += 1;

    // Construct type match
    if !rule.construct_type.is_empty() && rule.construct_type == construct.node_type {
        score += 1.5;
    }
    checks += 1;

    // Import pattern match
    for import_pattern in &rule.match_pattern.imports {
        if construct.node_text.contains(import_pattern.as_str())
            || construct.node_name.contains(import_pattern.as_str())
        {
            score += 1.0;
        }
    }

    // Client name match
    for client_pattern in &rule.match_pattern.client_names {
        if construct.node_name.contains(client_pattern.as_str())
            || construct.node_text.contains(client_pattern.as_str())
        {
            score += 1.5;
        }
    }

    // Method name match
    for method_pattern in &rule.match_pattern.method_names {
        if construct.node_name.contains(method_pattern.as_str())
            || construct.node_text.contains(method_pattern.as_str())
        {
            score += 1.0;
        }
    }

    // Resource type match
    if let Some(resource_type) = construct.metadata.get("resource_type") {
        for rt_pattern in &rule.match_pattern.resource_types {
            if resource_type == rt_pattern {
                score += 2.0;
            }
        }
    }

    // Text pattern match
    for text_pattern in &rule.match_pattern.text_patterns {
        if construct.node_text.contains(text_pattern.as_str()) {
            score += 0.5;
        }
    }

    if checks > 0 {
        score
    } else {
        0.0
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pattern_engine::catalogue::*;
    use std::collections::HashMap;

    fn make_s3_rule() -> PatternRule {
        PatternRule {
            id: "aws-s3-client-to-gcs".into(),
            name: "S3 client to GCS".into(),
            description: String::new(),
            source_provider: "aws".into(),
            target_provider: "gcp".into(),
            source_service: "s3".into(),
            target_service: "gcs".into(),
            language: "python".into(),
            construct_type: "client_init".into(),
            match_pattern: MatchPattern {
                imports: vec!["boto3".into()],
                client_names: vec!["boto3.client".into()],
                method_names: vec![],
                resource_types: vec![],
                text_patterns: vec![],
            },
            transform: TransformSpec {
                replacement_template: "storage.Client()".into(),
                import_additions: vec!["from google.cloud import storage".into()],
                import_removals: vec!["import boto3".into()],
                notes: String::new(),
            },
            base_confidence: 0.90,
            tags: vec![],
            examples: vec![],
        }
    }

    #[test]
    fn test_find_best_match() {
        let mut cat = RuleCatalogue::new();
        cat.add_rule(make_s3_rule());

        let construct = MatchConstruct {
            node_type: "client_init".into(),
            node_name: "boto3.client".into(),
            node_text: "boto3.client('s3')".into(),
            provider: "aws".into(),
            service: "s3".into(),
            language: "python".into(),
            metadata: HashMap::new(),
        };

        let result = find_best_match(&cat, &construct);
        assert!(result.is_some());
        assert_eq!(result.unwrap().id, "aws-s3-client-to-gcs");
    }

    #[test]
    fn test_no_match_wrong_service() {
        let mut cat = RuleCatalogue::new();
        cat.add_rule(make_s3_rule());

        let construct = MatchConstruct {
            node_type: "client_init".into(),
            node_name: "boto3.client".into(),
            node_text: "boto3.client('dynamodb')".into(),
            provider: "aws".into(),
            service: "dynamodb".into(),
            language: "python".into(),
            metadata: HashMap::new(),
        };

        let result = find_best_match(&cat, &construct);
        assert!(result.is_none());
    }
}

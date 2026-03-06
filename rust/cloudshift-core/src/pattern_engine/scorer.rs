use super::catalogue::PatternRule;

pub struct ScoringFactors {
    pub specificity: f64,
    pub version_match: f64,
    pub usage_frequency: f64,
}

impl Default for ScoringFactors {
    fn default() -> Self {
        ScoringFactors {
            specificity: 1.0,
            version_match: 1.0,
            usage_frequency: 1.0,
        }
    }
}

pub fn adjust_confidence(rule: &PatternRule, factors: &ScoringFactors) -> f64 {
    let base = rule.base_confidence;

    // Specificity: more specific patterns get higher confidence
    let specificity_bonus = (factors.specificity - 1.0) * 0.05;

    // Version match: matching SDK version boosts confidence
    let version_bonus = (factors.version_match - 1.0) * 0.03;

    // Usage frequency: well-tested patterns get a small boost
    let usage_bonus = (factors.usage_frequency.ln() * 0.01).min(0.05).max(0.0);

    let adjusted = base + specificity_bonus + version_bonus + usage_bonus;

    // Clamp to [0.0, 1.0]
    adjusted.clamp(0.0, 1.0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pattern_engine::catalogue::*;

    #[test]
    fn test_default_scoring() {
        let rule = PatternRule {
            id: "test".into(),
            name: "Test".into(),
            description: String::new(),
            source_provider: "aws".into(),
            target_provider: "gcp".into(),
            source_service: "s3".into(),
            target_service: "gcs".into(),
            language: "python".into(),
            construct_type: String::new(),
            match_pattern: MatchPattern {
                imports: vec![],
                client_names: vec![],
                method_names: vec![],
                resource_types: vec![],
                text_patterns: vec![],
            },
            transform: TransformSpec {
                replacement_template: String::new(),
                import_additions: vec![],
                import_removals: vec![],
                notes: String::new(),
            },
            base_confidence: 0.85,
            tags: vec![],
            examples: vec![],
        };

        let factors = ScoringFactors::default();
        let adjusted = adjust_confidence(&rule, &factors);
        assert!((adjusted - 0.85).abs() < 0.001);
    }
}

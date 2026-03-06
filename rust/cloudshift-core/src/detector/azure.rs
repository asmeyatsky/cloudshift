use std::collections::HashMap;

use crate::parser::{AstNode, NodeType};

use super::{CloudProvider, ServiceDetection};

pub fn detect(node: &AstNode) -> Option<ServiceDetection> {
    match &node.node_type {
        NodeType::Import => detect_import(node),
        NodeType::ClientInit => detect_client_init(node),
        NodeType::ResourceBlock => detect_resource_block(node),
        NodeType::StringLiteral => detect_azure_reference(node),
        NodeType::EnvVar => detect_env_var(node),
        _ => None,
    }
}

fn detect_import(node: &AstNode) -> Option<ServiceDetection> {
    let text = &node.text;
    let name = &node.name;

    // Python azure-sdk
    if name.starts_with("azure.") || text.contains("azure.") {
        let service = extract_azure_service(text);
        return Some(ServiceDetection {
            provider: CloudProvider::Azure,
            service,
            construct_type: "import".to_string(),
            confidence: 0.95,
            node_name: node.name.clone(),
            start_line: node.start_line,
            end_line: node.end_line,
            metadata: HashMap::new(),
        });
    }

    // TypeScript @azure
    if name.contains("@azure") || text.contains("@azure") {
        let service = extract_azure_ts_service(text);
        return Some(ServiceDetection {
            provider: CloudProvider::Azure,
            service,
            construct_type: "import".to_string(),
            confidence: 0.95,
            node_name: node.name.clone(),
            start_line: node.start_line,
            end_line: node.end_line,
            metadata: HashMap::new(),
        });
    }

    None
}

fn detect_client_init(node: &AstNode) -> Option<ServiceDetection> {
    let name = &node.name;
    let text = &node.text;

    let azure_clients = [
        ("BlobServiceClient", "blob-storage"),
        ("ContainerClient", "blob-storage"),
        ("BlobClient", "blob-storage"),
        ("QueueServiceClient", "queue-storage"),
        ("TableServiceClient", "table-storage"),
        ("ServiceBusClient", "servicebus"),
        ("EventHubProducerClient", "eventhub"),
        ("EventHubConsumerClient", "eventhub"),
        ("CosmosClient", "cosmosdb"),
        ("SecretClient", "keyvault"),
        ("KeyClient", "keyvault"),
        ("CertificateClient", "keyvault"),
        ("ComputeManagementClient", "compute"),
        ("NetworkManagementClient", "network"),
        ("ResourceManagementClient", "resource"),
        ("SqlManagementClient", "sql"),
    ];

    for (client_name, service) in &azure_clients {
        if name.contains(client_name) || text.contains(client_name) {
            return Some(ServiceDetection {
                provider: CloudProvider::Azure,
                service: service.to_string(),
                construct_type: "client_init".to_string(),
                confidence: 0.95,
                node_name: node.name.clone(),
                start_line: node.start_line,
                end_line: node.end_line,
                metadata: HashMap::new(),
            });
        }
    }

    None
}

fn detect_resource_block(node: &AstNode) -> Option<ServiceDetection> {
    let resource_type = node
        .metadata
        .get("resource_type")
        .map(|s| s.as_str())
        .unwrap_or("");

    // Terraform azurerm_ resources
    if resource_type.starts_with("azurerm_") {
        let service = extract_terraform_azure_service(resource_type);
        return Some(ServiceDetection {
            provider: CloudProvider::Azure,
            service,
            construct_type: "resource_block".to_string(),
            confidence: 0.98,
            node_name: node.name.clone(),
            start_line: node.start_line,
            end_line: node.end_line,
            metadata: node.metadata.clone(),
        });
    }

    // ARM template resource types: Microsoft.Storage/storageAccounts
    if resource_type.starts_with("Microsoft.") {
        let service = extract_arm_service(resource_type);
        return Some(ServiceDetection {
            provider: CloudProvider::Azure,
            service,
            construct_type: "resource_block".to_string(),
            confidence: 0.98,
            node_name: node.name.clone(),
            start_line: node.start_line,
            end_line: node.end_line,
            metadata: node.metadata.clone(),
        });
    }

    None
}

fn detect_azure_reference(node: &AstNode) -> Option<ServiceDetection> {
    if node.text.contains(".azure.") || node.text.contains("management.azure.com") {
        return Some(ServiceDetection {
            provider: CloudProvider::Azure,
            service: "endpoint".to_string(),
            construct_type: "endpoint_reference".to_string(),
            confidence: 0.85,
            node_name: node.name.clone(),
            start_line: node.start_line,
            end_line: node.end_line,
            metadata: HashMap::new(),
        });
    }
    None
}

fn detect_env_var(node: &AstNode) -> Option<ServiceDetection> {
    let azure_env_patterns = [
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "AZURE_TENANT_ID",
        "AZURE_SUBSCRIPTION_ID",
        "AZURE_STORAGE_CONNECTION_STRING",
        "AZURE_STORAGE_ACCOUNT",
    ];

    for pattern in &azure_env_patterns {
        if node.text.contains(pattern) {
            return Some(ServiceDetection {
                provider: CloudProvider::Azure,
                service: "credentials".to_string(),
                construct_type: "env_var".to_string(),
                confidence: 0.90,
                node_name: node.name.clone(),
                start_line: node.start_line,
                end_line: node.end_line,
                metadata: HashMap::new(),
            });
        }
    }

    None
}

fn extract_azure_service(text: &str) -> String {
    if text.contains("azure.storage") {
        "blob-storage".to_string()
    } else if text.contains("azure.servicebus") {
        "servicebus".to_string()
    } else if text.contains("azure.cosmos") {
        "cosmosdb".to_string()
    } else if text.contains("azure.keyvault") {
        "keyvault".to_string()
    } else if text.contains("azure.eventhub") {
        "eventhub".to_string()
    } else if text.contains("azure.identity") {
        "identity".to_string()
    } else if text.contains("azure.mgmt") {
        "management".to_string()
    } else {
        "sdk".to_string()
    }
}

fn extract_azure_ts_service(text: &str) -> String {
    if text.contains("storage-blob") {
        "blob-storage".to_string()
    } else if text.contains("service-bus") {
        "servicebus".to_string()
    } else if text.contains("cosmos") {
        "cosmosdb".to_string()
    } else if text.contains("keyvault") {
        "keyvault".to_string()
    } else if text.contains("event-hubs") {
        "eventhub".to_string()
    } else if text.contains("identity") {
        "identity".to_string()
    } else {
        "sdk".to_string()
    }
}

fn extract_terraform_azure_service(resource_type: &str) -> String {
    let without_prefix = resource_type.strip_prefix("azurerm_").unwrap_or(resource_type);
    let service_map = [
        ("storage_", "blob-storage"),
        ("cosmosdb_", "cosmosdb"),
        ("servicebus_", "servicebus"),
        ("eventhub_", "eventhub"),
        ("key_vault", "keyvault"),
        ("virtual_machine", "compute"),
        ("virtual_network", "network"),
        ("subnet", "network"),
        ("network_security_group", "network"),
        ("sql_", "sql"),
        ("function_app", "functions"),
        ("app_service", "appservice"),
        ("container_", "containers"),
        ("kubernetes_", "aks"),
        ("redis_", "redis"),
        ("dns_", "dns"),
        ("lb_", "loadbalancer"),
        ("resource_group", "resource"),
    ];

    for (prefix, service) in &service_map {
        if without_prefix.starts_with(prefix) {
            return service.to_string();
        }
    }

    without_prefix
        .split('_')
        .next()
        .unwrap_or("unknown")
        .to_string()
}

fn extract_arm_service(resource_type: &str) -> String {
    // Microsoft.Storage/storageAccounts -> storage
    let parts: Vec<&str> = resource_type.split('.').collect();
    if parts.len() >= 2 {
        let namespace = parts[1].split('/').next().unwrap_or("unknown");
        return namespace.to_lowercase();
    }
    "unknown".to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detect_azure_import() {
        let node = AstNode {
            node_type: NodeType::Import,
            name: "azure.storage.blob".into(),
            text: "from azure.storage.blob import BlobServiceClient".into(),
            start_line: 1,
            end_line: 1,
            start_col: 0,
            end_col: 48,
            children: vec![],
            metadata: HashMap::new(),
        };
        let detection = detect(&node).unwrap();
        assert_eq!(detection.provider, CloudProvider::Azure);
        assert_eq!(detection.service, "blob-storage");
    }

    #[test]
    fn test_detect_azurerm_resource() {
        let mut metadata = HashMap::new();
        metadata.insert(
            "resource_type".to_string(),
            "azurerm_storage_account".to_string(),
        );
        let node = AstNode {
            node_type: NodeType::ResourceBlock,
            name: "azurerm_storage_account.example".into(),
            text: "resource \"azurerm_storage_account\" \"example\" {}".into(),
            start_line: 1,
            end_line: 3,
            start_col: 0,
            end_col: 1,
            children: vec![],
            metadata,
        };
        let detection = detect(&node).unwrap();
        assert_eq!(detection.provider, CloudProvider::Azure);
        assert_eq!(detection.service, "blob-storage");
    }
}

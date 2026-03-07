output "storage_account_name" {
  value = azurerm_storage_account.main.name
}

output "cosmos_endpoint" {
  value = azurerm_cosmosdb_account.main.endpoint
}

output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.main.name
}

output "function_app_url" {
  value = azurerm_linux_function_app.api.default_hostname
}

output "servicebus_namespace" {
  value = azurerm_servicebus_namespace.main.name
}

output "sql_server_fqdn" {
  value = azurerm_mssql_server.main.fully_qualified_domain_name
}

output "keyvault_uri" {
  value = azurerm_key_vault.main.vault_uri
}

output "public_ip" {
  value = azurerm_public_ip.main.ip_address
}

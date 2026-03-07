resource "azurerm_servicebus_namespace" "main" {
  name                = "myapp-servicebus"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard"

  tags = {
    environment = "production"
  }
}

resource "azurerm_servicebus_queue" "orders" {
  name         = "orders"
  namespace_id = azurerm_servicebus_namespace.main.id

  max_delivery_count  = 5
  lock_duration       = "PT1M"
  default_message_ttl = "P14D"

  dead_lettering_on_message_expiration = true
}

resource "azurerm_servicebus_topic" "notifications" {
  name         = "notifications"
  namespace_id = azurerm_servicebus_namespace.main.id
}

resource "azurerm_servicebus_subscription" "email" {
  name     = "email-sub"
  topic_id = azurerm_servicebus_topic.notifications.id

  max_delivery_count = 3
}

resource "azurerm_eventhub_namespace" "analytics" {
  name                = "myapp-eventhub"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard"
  capacity            = 2
}

resource "azurerm_eventhub" "events" {
  name                = "app-events"
  namespace_name      = azurerm_eventhub_namespace.analytics.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = 4
  message_retention   = 7
}

# Service Bus Namespace
resource "azurerm_servicebus_namespace" "main" {
  name                = "sb-${local.prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Standard"
}

# Service Bus Topic for new submissions
resource "azurerm_servicebus_topic" "new_submissions" {
  name                = "new-submissions"
  namespace_id        = azurerm_servicebus_namespace.main.id
  
  # Configure message settings
  max_size_in_megabytes   = 1024
  default_message_ttl     = "P14D"  # 14 days
  duplicate_detection_history_time_window = "PT10M"  # 10 minutes
  
  # Enable partitioning for better performance
  partitioning_enabled = true
}

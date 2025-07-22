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

# Service Bus Subscription for submission-intake service
resource "azurerm_servicebus_subscription" "submission_intake" {
  name                = "submission-intake"
  topic_id            = azurerm_servicebus_topic.new_submissions.id
  
  # Configure subscription settings
  max_delivery_count  = 10
  default_message_ttl = "P14D"  # 14 days
  
  # Enable dead lettering for expired messages
  dead_lettering_on_message_expiration = true
  dead_lettering_on_filter_evaluation_error = true
}

# Service Bus Subscription for Logic App
resource "azurerm_servicebus_subscription" "submission_intake_logicapp" {
  name                = "submission-intake-logicapp"
  topic_id            = azurerm_servicebus_topic.new_submissions.id
  
  # Configure subscription settings
  max_delivery_count  = 10
  default_message_ttl = "P14D"  # 14 days
  
  # Enable dead lettering for expired messages
  dead_lettering_on_message_expiration = true
  dead_lettering_on_filter_evaluation_error = true
}

# Service Bus Topic for processed submissions
resource "azurerm_servicebus_topic" "processed_submissions" {
  name                = "processed-submissions"
  namespace_id        = azurerm_servicebus_namespace.main.id
  
  # Configure message settings
  max_size_in_megabytes   = 1024
  default_message_ttl     = "P14D"  # 14 days
  duplicate_detection_history_time_window = "PT10M"  # 10 minutes
  
  # Enable partitioning for better performance
  partitioning_enabled = true
}

# Service Bus Subscription for processed submissions
resource "azurerm_servicebus_subscription" "processed_submissions" {
  name                = "processed-submissions-consumer"
  topic_id            = azurerm_servicebus_topic.processed_submissions.id
  
  # Configure subscription settings
  max_delivery_count  = 10
  default_message_ttl = "P14D"  # 14 days
  
  # Enable dead lettering for expired messages
  dead_lettering_on_message_expiration = true
  dead_lettering_on_filter_evaluation_error = true
}

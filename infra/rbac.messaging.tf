# RBAC assignments for Azure Service Bus messaging

# Current user Service Bus permissions for local development
resource "azurerm_role_assignment" "current_user_service_bus_sender" {
  scope                = azurerm_servicebus_namespace.main.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "current_user_service_bus_receiver" {
  scope                = azurerm_servicebus_namespace.main.id
  role_definition_name = "Azure Service Bus Data Receiver"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Client Web service Service Bus permissions
resource "azurerm_role_assignment" "client_web_service_bus_sender" {
  scope                = azurerm_servicebus_namespace.main.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_user_assigned_identity.client_web.principal_id
}

# Submission Intake service Service Bus permissions
resource "azurerm_role_assignment" "submission_intake_service_bus_receiver" {
  scope                = azurerm_servicebus_namespace.main.id
  role_definition_name = "Azure Service Bus Data Receiver"
  principal_id         = azurerm_user_assigned_identity.submission_intake.principal_id
}

# Submission Trigger service Service Bus permissions
resource "azurerm_role_assignment" "submission_trigger_service_bus_sender" {
  scope                = azurerm_servicebus_namespace.main.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_user_assigned_identity.submission_trigger.principal_id
}

resource "azurerm_role_assignment" "submission_trigger_service_bus_receiver" {
  scope                = azurerm_servicebus_namespace.main.id
  role_definition_name = "Azure Service Bus Data Receiver"
  principal_id         = azurerm_user_assigned_identity.submission_trigger.principal_id
}

# Submission Analyzer service Service Bus permissions
resource "azurerm_role_assignment" "submission_analyzer_service_bus_sender" {
  scope                = azurerm_servicebus_namespace.main.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_user_assigned_identity.submission_analyzer.principal_id
}

resource "azurerm_role_assignment" "submission_analyzer_service_bus_receiver" {
  scope                = azurerm_servicebus_namespace.main.id
  role_definition_name = "Azure Service Bus Data Receiver"
  principal_id         = azurerm_user_assigned_identity.submission_analyzer.principal_id
}

# Logic App Service Bus permissions
# Note: Logic App Standard built-in connectors require system-assigned identity
# and need "Azure Service Bus Data Owner" role for full access including management operations
resource "azurerm_role_assignment" "logic_app_service_bus_owner" {
  scope                = azurerm_servicebus_namespace.main.id
  role_definition_name = "Azure Service Bus Data Owner"
  principal_id         = azapi_resource.logic_app.identity[0].principal_id
}

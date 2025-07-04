# Logic App Workflow (Multitenant/Consumption)
resource "azurerm_logic_app_workflow" "main" {
  name                = "logic-${local.prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  # Enable managed identity
  identity {
    type = "SystemAssigned"
  }
}

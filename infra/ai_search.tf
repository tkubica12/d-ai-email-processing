resource "azurerm_search_service" "main" {
  name                         = "search-${local.prefix}"
  resource_group_name          = azurerm_resource_group.main.name
  location                     = azurerm_resource_group.main.location
  sku                          = "standard"
  local_authentication_enabled = true
  semantic_search_sku          = "standard"
  authentication_failure_mode  = "http401WithBearerChallenge"

  identity {
    type = "SystemAssigned"
  }
}

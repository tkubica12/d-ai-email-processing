resource "azurerm_cognitive_account" "document_intelligence" {
  name                          = "${local.prefix}-docintel"
  location                      = var.location
  resource_group_name           = azurerm_resource_group.main.name
  kind                          = "FormRecognizer"
  sku_name                      = "S0"
  custom_subdomain_name         = "${local.prefix}-docintel"
  public_network_access_enabled = true
}

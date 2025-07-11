# Generate random string for resource naming uniqueness
resource "random_string" "suffix" {
  length  = 4
  special = false
  upper   = false
  numeric = false
}

# Common locals for resource naming and tagging
locals {
  environment = var.environment_name
  location    = var.location
  prefix      = "${var.project_name}-${local.environment}-${random_string.suffix.result}"
  base_name   = "${var.project_name}-${local.environment}-${random_string.suffix.result}"

  # Special naming for resources with strict naming requirements
  storage_prefix = "${replace(var.project_name, "-", "")}${local.environment}${random_string.suffix.result}"
}

# Get current client configuration
data "azurerm_client_config" "current" {}
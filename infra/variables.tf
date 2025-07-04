variable "environment_name" {
  description = "The environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "The Azure region where resources will be created"
  type        = string
  default     = "swedencentral"
}

variable "project_name" {
  description = "The name of the project"
  type        = string
  default     = "email"
}

variable "email_mailbox" {
  description = "The email mailbox to monitor for incoming emails"
  type        = string
  default     = ""
}

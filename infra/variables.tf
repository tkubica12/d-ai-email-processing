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

variable "github_repository" {
  description = "The GitHub repository name in the format owner/repo"
  type        = string
  default     = "tkubica12/d-ai-email-processing"
}

variable "container_app_cooldown_period" {
  description = "The cooldown period for container app scaling"
  type        = string
  default     = "300s"
}

variable "container_app_min_replicas" {
  description = "The minimum number of replicas for container apps"
  type        = number
  default     = 0
}

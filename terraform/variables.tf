variable "project_id" {
  description = "The GCP Project ID"
  type        = string
  default     = "gen-lang-client-0930334575"
}

variable "project" {
  description = "Project name"
  type        = string
  default     = "nexusedu"
}

variable "vm_type" {
  type    = string
  default = "e2-medium"
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP zone"
  type        = string
  default     = "us-central1-a"
}

variable "db_username" {
  type        = string
  description = "The username for the database"
  default     = "nexusedu_user" # Optional default
}

variable "db_password" {
  description = "Password for the database user"
  type        = string
  sensitive   = true
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "nexusedu"
}

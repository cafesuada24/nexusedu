variable "project_id" {
  description = "The GCP Project ID"
  type        = string
  default     = "gen-lang-client-0930334575"
}

variable "project" {
  description = "Project name"
  type = string
  default = "nexusedu"
}

variable "public_subnet_cidr" {
  type = string
  default = "10.0.1.0/24"
}

variable "private_subnet_cidr" {
  type = string
  default = "10.0.2.0/24"
}

variable "admin_ip_cidr" {
  type = string
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

variable "db_instance_name" {
  description = "Name of the Cloud SQL instance"
  type        = string
  default     = "nexusedu-db"
}

variable "vm_name" {
  description = "Name of the Compute Engine VM"
  type        = string
  default     = "nexusedu-api-server"
}

variable "vm_machine_type" {
  description = "Machine type for the VM"
  type        = string
  default     = "e2-standard-2"
}

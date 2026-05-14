output "vm_public_ip" {
  description = "The public IP of the Compute Engine instance"
  value       = google_compute_address.static_ip.address
}

output "db_private_ip" {
  description = "The private IP of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.private_ip_address
}

output "db_connection_name" {
  description = "The connection name of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.connection_name
}

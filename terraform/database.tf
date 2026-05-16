resource "google_sql_database_instance" "postgres" {
  name             = "${var.project}-postgres"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier    = "db-f1-micro"
    edition = "ENTERPRISE"

    ip_configuration {
      ipv4_enabled = true

      authorized_networks {
        name  = "vm-access"
        value = google_compute_address.static_ip.address
      }
    }

    backup_configuration {
      enabled = true
    }
  }

  deletion_protection = false
}

resource "google_sql_database" "app_db" {
  name     = var.db_name
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "app_user" {
  name     = var.db_username
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}

resource "google_project_iam_member" "cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"

  member = "serviceAccount:${google_service_account.app.email}"
}

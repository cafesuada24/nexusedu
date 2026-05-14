#############################################
# Service Account
#############################################

resource "google_service_account" "api" {
  account_id   = "${var.project}-api"
  display_name = "API Server Service Account"
}

#############################################
# Static External IP
#############################################

resource "google_compute_address" "static_ip" {
  name   = "${local.name_prefix}-static-ip"
  region = var.region
}

#############################################
# Compute Engine VM
#############################################

resource "google_compute_instance" "api_server" {
  name         = "${local.name_prefix}-api"
  machine_type = var.vm_machine_type
  zone         = var.zone

  deletion_protection = false

  ###########################################
  # Shielded VM
  ###########################################

  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  ###########################################
  # Boot Disk
  ###########################################

  boot_disk {
    auto_delete = true

    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
      size  = 40
      type  = "pd-ssd"
    }
  }

  ###########################################
  # Network
  ###########################################

  network_interface {
    subnetwork = google_compute_subnetwork.public.id

    access_config {
      nat_ip = google_compute_address.static_ip.address
    }
  }

  ###########################################
  # Metadata
  ###########################################

  metadata = {
    enable-oslogin = "TRUE"
  }

  metadata_startup_script = file(
    "${path.module}/scripts/startup.sh"
  )

  ###########################################
  # Service Account
  ###########################################

  service_account {
    email = google_service_account.api.email

    scopes = [
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring.write",
    ]
  }

  ###########################################
  # Labels
  ###########################################

  labels = {
    service     = "api"
  }

  ###########################################
  # Lifecycle
  ###########################################

  lifecycle {
    ignore_changes = [
      metadata_startup_script
    ]
  }
}

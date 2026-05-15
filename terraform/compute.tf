resource "google_compute_address" "static_ip" {
  name   = "${var.project}-static-ip"
  region = var.region
}

resource "google_service_account" "app" {
  account_id   = "${var.project}-app"
  display_name = "Application Service Account"
}

resource "google_compute_instance" "api" {
  name         = "${var.project}-api"
  machine_type = "e2-micro"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
      size  = 20
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.public.id

    access_config {
      nat_ip = google_compute_address.static_ip.address
    }
  }

  metadata = {
    enable-oslogin = "TRUE"
  }

  service_account {
    email = google_service_account.app.email

    scopes = [
      "cloud-platform"
    ]
  }

  tags = ["web"]
}

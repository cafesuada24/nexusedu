resource "google_compute_network" "vpc" {
  name                    = "${var.project}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "public" {
  name          = "${var.project}-subnet"
  region        = var.region
  network       = google_compute_network.vpc.id
  ip_cidr_range = "10.10.0.0/24"

  private_ip_google_access = true
}

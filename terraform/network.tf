#############################################
# Locals
#############################################

locals {
  name_prefix = var.project
}

#############################################
# VPC
#############################################

resource "google_compute_network" "vpc" {
  name                    = "${local.name_prefix}-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

#############################################
# Public Subnet
#############################################

resource "google_compute_subnetwork" "public" {
  name          = "${local.name_prefix}-public-subnet"
  ip_cidr_range = var.public_subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc.id

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

#############################################
# Private Subnet
#############################################

resource "google_compute_subnetwork" "private" {
  name          = "${local.name_prefix}-private-subnet"
  ip_cidr_range = var.private_subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc.id

  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

#############################################
# Private Services Access
# (Cloud SQL Private IP)
#############################################

resource "google_compute_global_address" "private_service_access" {
  name          = "${local.name_prefix}-psa-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [
    google_compute_global_address.private_service_access.name
  ]
}

#############################################
# Cloud Router
#############################################

resource "google_compute_router" "router" {
  name    = "${local.name_prefix}-router"
  region  = var.region
  network = google_compute_network.vpc.id
}

#############################################
# Cloud NAT
#############################################

resource "google_compute_router_nat" "nat" {
  name                               = "${local.name_prefix}-nat"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"

  subnetwork {
    name                    = google_compute_subnetwork.private.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }
}

#############################################
# Firewall - HTTP
#############################################

resource "google_compute_firewall" "allow_http" {
  name    = "${local.name_prefix}-allow-http"
  network = google_compute_network.vpc.name

  direction = "INGRESS"
  priority  = 1000

  allow {
    protocol = "tcp"
    ports    = ["80"]
  }

  source_ranges = ["0.0.0.0/0"]

  target_service_accounts = [
    google_service_account.app.email
  ]

  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }
}

#############################################
# Firewall - HTTPS
#############################################

resource "google_compute_firewall" "allow_https" {
  name    = "${local.name_prefix}-allow-https"
  network = google_compute_network.vpc.name

  direction = "INGRESS"
  priority  = 1000

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }

  source_ranges = ["0.0.0.0/0"]

  target_service_accounts = [
    google_service_account.app.email
  ]

  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }
}

#############################################
# Firewall - Internal Traffic
#############################################

resource "google_compute_firewall" "allow_internal" {
  name    = "${local.name_prefix}-allow-internal"
  network = google_compute_network.vpc.name

  direction = "INGRESS"
  priority  = 1000

  allow {
    protocol = "tcp"
  }

  allow {
    protocol = "udp"
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [
    var.public_subnet_cidr,
    var.private_subnet_cidr
  ]

  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }
}

#############################################
# Firewall - SSH
# Restrict to Admin IP
#############################################

resource "google_compute_firewall" "allow_ssh" {
  name    = "${local.name_prefix}-allow-ssh"
  network = google_compute_network.vpc.name

  direction = "INGRESS"
  priority  = 1000

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = [var.admin_ip_cidr]

  target_service_accounts = [
    google_service_account.app.email
  ]

  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }
}

#############################################
# Service Account
#############################################

resource "google_service_account" "app" {
  account_id   = "${var.project}-app"
  display_name = "Application Service Account"
}

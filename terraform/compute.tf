# Static External IP for the VM
resource "google_compute_address" "static_ip" {
  name   = "${var.vm_name}-static-ip"
  region = var.region
}

# Compute Engine Instance
resource "google_compute_instance" "api_server" {
  name         = var.vm_name
  machine_type = var.vm_machine_type
  zone         = var.zone

  tags = ["http-server", "https-server"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
      size  = 40
      type  = "pd-ssd"
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.subnet.id
    access_config {
      nat_ip = google_compute_address.static_ip.address
    }
  }

  metadata_startup_script = file("${path.module}/scripts/startup.sh")

  service_account {
    # Best practice: Use a custom service account with minimal permissions
    scopes = ["cloud-platform"]
  }

  lifecycle {
    ignore_changes = [metadata_startup_script]
  }
}

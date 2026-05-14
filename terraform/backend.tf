terraform {
  backend "gcs" {
    bucket = "a20-007-backend"
    prefix = "terraform/state"
  }
}

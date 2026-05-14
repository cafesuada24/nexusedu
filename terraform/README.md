# GCP Infrastructure with Terraform

This directory contains the Terraform configuration to deploy the A20-App-007 backend infrastructure on Google Cloud Platform.

## Prerequisites

1.  **GCP Project:** Ensure you have a GCP project (Current: `gen-lang-client-0930334575`).
2.  **GCS Bucket:** Ensure the bucket `a20-007-backend` exists in your project for state management.
3.  **GCP Credentials:** Authenticate via Application Default Credentials:
    ```bash
    gcloud auth application-default login
    ```
4.  **Terraform:** Ensure Terraform v1.x is installed.

## Infrastructure Components

- **VPC:** Custom network `nexusedu-vpc` with private services access.
- **Cloud SQL:** PostgreSQL 16 instance (`db-f1-micro`) on a private IP.
- **Compute Engine:** `e2-standard-2` VM running Ubuntu 24.04 with Docker pre-installed via startup script.
- **Security:** Firewalls allowing HTTP (80), HTTPS (443), and SSH (22).

## How to Deploy

1.  **Configure Variables:**
    Copy the example vars file and update the `db_password`:
    ```bash
    cp terraform.tfvars.example terraform.tfvars
    # Edit terraform.tfvars with your desired database password
    ```

2.  **Initialize Terraform:**
    ```bash
    terraform init
    ```

3.  **Plan Deployment:**
    ```bash
    terraform plan
    ```

4.  **Apply Changes:**
    ```bash
    terraform apply
    ```

## Post-Deployment

After `terraform apply` finishes, it will output the `vm_public_ip` and `db_private_ip`.

1.  **SSH into VM:**
    ```bash
    gcloud compute ssh nexusedu-api-server --zone us-central1-a
    ```
2.  **Verify Docker:**
    ```bash
    docker --version
    docker compose version
    ```
3.  **Configure Application:**
    Create a `.env.production` file on the VM using the `db_private_ip` for the `DATABASE_URL`.

## Troubleshooting

### VPC Deletion Issues
If `terraform destroy` fails with an error like `Producer services are still using this connection` or `Network is already being used by routes`:

1.  **Wait:** GCP sometimes takes 2-5 minutes to release internal resources after Cloud SQL is deleted.
2.  **Manual Cleanup:** Run the provided helper script to force-clear the locks:
    ```bash
    chmod +x scripts/cleanup_vpc.sh
    ./scripts/cleanup_vpc.sh gen-lang-client-0930334575 nexusedu-vpc
    ```
    Alternatively, run the commands manually:
    ```bash
    # 1. Delete the VPC Peering (Service Networking)
    gcloud compute networks peerings delete servicenetworking-googleapis-com --network=nexusedu-vpc
    
    # 2. Delete any residual routes if necessary
    # (Replace ROUTE_NAME with the one from the error message)
    gcloud compute routes delete ROUTE_NAME
    
    # 3. Retry Terraform Destroy
    terraform destroy
    ```

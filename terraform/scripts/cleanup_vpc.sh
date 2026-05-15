#!/bin/bash
# Helper script to clean up VPC dependencies that block terraform destroy
# Usage: ./cleanup_vpc.sh <project_id> <network_name>

PROJECT_ID=$1
NETWORK_NAME=$2

if [[ -z "$PROJECT_ID" || -z "$NETWORK_NAME" ]]; then
    echo "Usage: $0 <project_id> <network_name>"
    exit 1
fi

echo "Cleaning up dependencies for VPC: $NETWORK_NAME in project: $PROJECT_ID"

# 1. Delete Service Networking Peering
echo "Attempting to delete Service Networking peering..."
gcloud compute networks peerings delete servicenetworking-googleapis-com \
    --network="$NETWORK_NAME" \
    --project="$PROJECT_ID" \
    --quiet || echo "Peering already deleted or not found."

# 2. Find and delete residual routes
echo "Checking for residual routes..."
ROUTES=$(gcloud compute routes list --filter="network:$NETWORK_NAME" --project="$PROJECT_ID" --format="value(name)")
for ROUTE in $ROUTES; do
    echo "Deleting route: $ROUTE"
    gcloud compute routes delete "$ROUTE" --project="$PROJECT_ID" --quiet
done

# 3. Delete reserved IP range if it exists
echo "Checking for reserved IP ranges..."
gcloud compute addresses delete google-managed-services-range \
    --global \
    --project="$PROJECT_ID" \
    --quiet || echo "Reserved range already deleted or not found."

echo "Cleanup complete. You should now be able to run 'terraform destroy'."

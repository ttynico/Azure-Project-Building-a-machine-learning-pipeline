#!/usr/bin/env bash
# Creates the Azure resources needed to run the network anomaly pipeline.
# Run one section at a time and confirm each step before moving to the next.
set -euo pipefail

RESOURCE_GROUP="rg-ml-network-anomaly"
LOCATION="eastus"
WORKSPACE_NAME="mlw-network-anomaly"
COMPUTE_NAME="cpu-cluster"
VM_SIZE="Standard_DS3_v2"

echo "==> Ensuring Azure ML CLI extension is installed"
az extension add -n ml -y || az extension update -n ml

echo "==> Creating resource group: $RESOURCE_GROUP in $LOCATION"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

echo "==> Creating Azure ML workspace: $WORKSPACE_NAME"
az ml workspace create \
  --name "$WORKSPACE_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION"

echo "==> Creating compute cluster: $COMPUTE_NAME (scale-to-zero, max 2 nodes)"
az ml compute create \
  --name "$COMPUTE_NAME" \
  --type AmlCompute \
  --min-instances 0 \
  --max-instances 2 \
  --size "$VM_SIZE" \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$WORKSPACE_NAME"

echo "==> Done. Resources created:"
echo "    Resource group : $RESOURCE_GROUP"
echo "    Workspace      : $WORKSPACE_NAME"
echo "    Compute cluster: $COMPUTE_NAME ($VM_SIZE, min=0 max=2)"
echo ""
echo "Next: register the dataset (see README) and run: python pipeline.py"

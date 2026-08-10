#!/usr/bin/env bash
# Tears down all resources created by create_resources.sh.
# Run this after every test/demo session — the workspace's underlying
# storage account, key vault, and container registry bill even while the
# compute cluster is scaled to zero.
set -euo pipefail

RESOURCE_GROUP="rg-ml-network-anomaly"

echo "==> This will delete the entire resource group: $RESOURCE_GROUP"
echo "    (workspace, compute, storage, key vault, container registry — everything)"
read -p "Type the resource group name to confirm deletion: " CONFIRM

if [ "$CONFIRM" != "$RESOURCE_GROUP" ]; then
  echo "Confirmation did not match. Aborting — nothing was deleted."
  exit 1
fi

echo "==> Deleting resource group: $RESOURCE_GROUP"
az group delete --name "$RESOURCE_GROUP" --yes --no-wait

echo "==> Deletion initiated (running in background)."
echo "    Check status with: az group show --name $RESOURCE_GROUP"

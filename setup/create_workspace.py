"""
Creates the Azure ML workspace and compute cluster using the SDK directly.

This exists because the `az ml` CLI extension fails to install on some
Windows Python setups (pydantic-core has no prebuilt wheel for certain
bundled CLI Python versions, and building from source needs the Rust
tool 'maturin', which isn't available). The Python SDK doesn't have that
problem, so we use it here instead of `az ml workspace create` /
`az ml compute create`.

Usage:
    python setup/create_workspace.py
"""
import os

from azure.ai.ml import MLClient
from azure.ai.ml.entities import Workspace, AmlCompute
from azure.identity import DefaultAzureCredential

SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID", "bcf47805-ae92-4706-8cf2-13bdb2fe29ba")
RESOURCE_GROUP = os.environ.get("AZURE_RESOURCE_GROUP", "rg-ml-network-anomaly")
WORKSPACE_NAME = os.environ.get("AZURE_ML_WORKSPACE", "mlw-network-anomaly")
LOCATION = "eastus"
COMPUTE_NAME = "cpu-cluster"
VM_SIZE = "Standard_DS3_v2"


def main():
    credential = DefaultAzureCredential()

    ml_client = MLClient(
        credential,
        subscription_id=SUBSCRIPTION_ID,
        resource_group_name=RESOURCE_GROUP,
    )

    print(f"Creating workspace '{WORKSPACE_NAME}' in {RESOURCE_GROUP} ({LOCATION})...")
    workspace = Workspace(
        name=WORKSPACE_NAME,
        location=LOCATION,
        description="Network anomaly detection pipeline workspace",
    )
    ws_poller = ml_client.workspaces.begin_create(workspace)
    created_ws = ws_poller.result()
    print(f"Workspace created: {created_ws.name}")

    ws_client = MLClient(
        credential,
        subscription_id=SUBSCRIPTION_ID,
        resource_group_name=RESOURCE_GROUP,
        workspace_name=WORKSPACE_NAME,
    )

    print(f"Creating compute cluster '{COMPUTE_NAME}' ({VM_SIZE}, min=0 max=2)...")
    compute = AmlCompute(
        name=COMPUTE_NAME,
        size=VM_SIZE,
        min_instances=0,
        max_instances=2,
        idle_time_before_scale_down=300,
    )
    compute_poller = ws_client.compute.begin_create_or_update(compute)
    created_compute = compute_poller.result()
    print(f"Compute cluster created: {created_compute.name}")

    print("\nDone. Resources created:")
    print(f"  Resource group : {RESOURCE_GROUP}")
    print(f"  Workspace      : {WORKSPACE_NAME}")
    print(f"  Compute cluster: {COMPUTE_NAME} ({VM_SIZE}, min=0 max=2)")


if __name__ == "__main__":
    main()

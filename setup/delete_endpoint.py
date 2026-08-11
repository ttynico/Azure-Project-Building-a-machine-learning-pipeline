"""
Deletes the online endpoint created by deploy_endpoint.py - the always-on,
billing part of this project. Run this as soon as you're done testing.

Usage:
    python setup/delete_endpoint.py
"""
import os

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential

SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID", "bcf47805-ae92-4706-8cf2-13bdb2fe29ba")
RESOURCE_GROUP = os.environ.get("AZURE_RESOURCE_GROUP", "rg-ml-network-anomaly")
WORKSPACE_NAME = os.environ.get("AZURE_ML_WORKSPACE", "mlw-network-anomaly")


def main():
    ml_client = MLClient(
        DefaultAzureCredential(),
        subscription_id=SUBSCRIPTION_ID,
        resource_group_name=RESOURCE_GROUP,
        workspace_name=WORKSPACE_NAME,
    )

    with open(".last_endpoint_name") as f:
        endpoint_name = f.read().strip()

    print(f"Deleting endpoint: {endpoint_name} (this stops the billing VM)")
    ml_client.online_endpoints.begin_delete(endpoint_name).result()
    print("Endpoint deleted.")

    os.remove(".last_endpoint_name")


if __name__ == "__main__":
    main()

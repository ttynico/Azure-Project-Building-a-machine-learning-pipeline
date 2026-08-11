"""
Registers the local data/ folder (containing KDDTrain+.txt and KDDTest+.txt)
as an Azure ML data asset, so pipeline.py can reference it by name/version.

Usage:
    python setup/register_dataset.py
"""
import os

from azure.ai.ml import MLClient
from azure.ai.ml.entities import Data
from azure.ai.ml.constants import AssetTypes
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

    data_asset = Data(
        name="nsl-kdd-raw",
        version="1",
        path="./data",
        type=AssetTypes.URI_FOLDER,
        description="NSL-KDD network intrusion detection dataset (KDDTrain+/KDDTest+)",
    )

    registered = ml_client.data.create_or_update(data_asset)
    print(f"Registered data asset: {registered.name}, version {registered.version}")
    print(f"Asset ID: {registered.id}")


if __name__ == "__main__":
    main()

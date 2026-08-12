"""
Deploys the registered 'network-anomaly-detector' model to a managed online
endpoint for real-time scoring.

Cost warning: online endpoints run on an always-on VM and bill hourly
regardless of traffic (~$70-140/mo for a small instance). This is meant to
be stood up, tested, and torn down with setup/delete_endpoint.py - not left
running.

Usage:
    python setup/deploy_endpoint.py
"""
import os
import uuid

from azure.ai.ml import MLClient
from azure.ai.ml.entities import (
    ManagedOnlineEndpoint,
    ManagedOnlineDeployment,
    Model,
    Environment,
    CodeConfiguration,
)
from azure.identity import DefaultAzureCredential

SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID", "bcf47805-ae92-4706-8cf2-13bdb2fe29ba")
RESOURCE_GROUP = os.environ.get("AZURE_RESOURCE_GROUP", "rg-ml-network-anomaly")
WORKSPACE_NAME = os.environ.get("AZURE_ML_WORKSPACE", "mlw-network-anomaly")

MODEL_NAME = "network-anomaly-detector"
MODEL_VERSION = "2"
ENDPOINT_NAME = f"network-anomaly-ep-{str(uuid.uuid4())[:8]}"
DEPLOYMENT_NAME = "blue"
INSTANCE_TYPE = "Standard_DS2_v2"


def main():
    ml_client = MLClient(
        DefaultAzureCredential(),
        subscription_id=SUBSCRIPTION_ID,
        resource_group_name=RESOURCE_GROUP,
        workspace_name=WORKSPACE_NAME,
    )

    model = ml_client.models.get(name=MODEL_NAME, version=MODEL_VERSION)

    print(f"Creating endpoint: {ENDPOINT_NAME}")
    endpoint = ManagedOnlineEndpoint(
        name=ENDPOINT_NAME,
        description="Real-time scoring for network intrusion detection",
        auth_mode="key",
    )
    ml_client.online_endpoints.begin_create_or_update(endpoint).result()
    print("Endpoint created.")

    env = Environment(
        name="network-anomaly-inference-env",
        conda_file="environment/conda-inference.yaml",
        image="mcr.microsoft.com/azureml/minimal-ubuntu22.04-py39-cpu-inference:latest",
    )

    print(f"Creating deployment: {DEPLOYMENT_NAME} on {INSTANCE_TYPE}")
    deployment = ManagedOnlineDeployment(
        name=DEPLOYMENT_NAME,
        endpoint_name=ENDPOINT_NAME,
        model=model,
        environment=env,
        code_configuration=CodeConfiguration(
            code="src/score",
            scoring_script="score.py",
        ),
        instance_type=INSTANCE_TYPE,
        instance_count=1,
    )
    ml_client.online_deployments.begin_create_or_update(deployment).result()
    print("Deployment created.")

    endpoint.traffic = {DEPLOYMENT_NAME: 100}
    ml_client.online_endpoints.begin_create_or_update(endpoint).result()
    print("Traffic routed 100% to deployment.")

    with open(".last_endpoint_name", "w") as f:
        f.write(ENDPOINT_NAME)

    scoring_uri = ml_client.online_endpoints.get(ENDPOINT_NAME).scoring_uri
    print(f"\nDone. Endpoint name: {ENDPOINT_NAME}")
    print(f"Scoring URI: {scoring_uri}")
    print("\nNext: python setup/test_endpoint.py")
    print("When finished testing: python setup/delete_endpoint.py")


if __name__ == "__main__":
    main()

"""
Defines and submits the network anomaly detection pipeline using the
Azure Machine Learning SDK v2 (azure-ai-ml).

Usage:
    python pipeline.py

Requires: az login, and resources created via setup/create_resources.sh
"""
import json
import os

from azure.ai.ml import MLClient, Input, Output, command
from azure.ai.ml.dsl import pipeline
from azure.ai.ml.entities import Environment, Model
from azure.ai.ml.constants import AssetTypes
from azure.identity import DefaultAzureCredential

# ---- Config -----------------------------------------------------------
SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID", "<your-subscription-id>")
RESOURCE_GROUP = os.environ.get("AZURE_RESOURCE_GROUP", "rg-ml-network-anomaly")
WORKSPACE_NAME = os.environ.get("AZURE_ML_WORKSPACE", "mlw-network-anomaly")
COMPUTE_TARGET = "cpu-cluster"
ACCURACY_THRESHOLD = 0.90
# -------------------------------------------------------------------------

ml_client = MLClient(
    DefaultAzureCredential(),
    subscription_id=SUBSCRIPTION_ID,
    resource_group_name=RESOURCE_GROUP,
    workspace_name=WORKSPACE_NAME,
)

env = Environment(
    name="network-anomaly-env",
    conda_file="environment/conda.yaml",
    image="mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu22.04",
)

# ---- Components ---------------------------------------------------------
data_prep_step = command(
    name="data_prep",
    display_name="Data preparation",
    code="src/data_prep",
    command=(
        "python data_prep.py "
        "--raw_data ${{inputs.raw_data}} "
        "--train_output ${{outputs.train_data}} "
        "--test_output ${{outputs.test_data}}"
    ),
    environment=env,
    compute=COMPUTE_TARGET,
    inputs={"raw_data": Input(type=AssetTypes.URI_FOLDER)},
    outputs={
        "train_data": Output(type=AssetTypes.URI_FOLDER),
        "test_data": Output(type=AssetTypes.URI_FOLDER),
    },
)

train_step = command(
    name="train",
    display_name="Train model",
    code="src/train",
    command=(
        "python train.py "
        "--train_data ${{inputs.train_data}} "
        "--model_output ${{outputs.model_output}}"
    ),
    environment=env,
    compute=COMPUTE_TARGET,
    inputs={"train_data": Input(type=AssetTypes.URI_FOLDER)},
    outputs={"model_output": Output(type=AssetTypes.URI_FOLDER)},
)

evaluate_step = command(
    name="evaluate",
    display_name="Evaluate model",
    code="src/evaluate",
    command=(
        "python evaluate.py "
        "--model_input ${{inputs.model_input}} "
        "--test_data ${{inputs.test_data}} "
        "--metrics_output ${{outputs.metrics_output}}"
    ),
    environment=env,
    compute=COMPUTE_TARGET,
    inputs={
        "model_input": Input(type=AssetTypes.URI_FOLDER),
        "test_data": Input(type=AssetTypes.URI_FOLDER),
    },
    outputs={"metrics_output": Output(type=AssetTypes.URI_FOLDER)},
)


# ---- Pipeline -------------------------------------------------------------
@pipeline(
    name="network_anomaly_detection_pipeline",
    display_name="Network Anomaly Detection Pipeline",
    compute=COMPUTE_TARGET,
)
def network_anomaly_pipeline(raw_data_input):
    prep = data_prep_step(raw_data=raw_data_input)
    train = train_step(train_data=prep.outputs.train_data)
    evaluate = evaluate_step(
        model_input=train.outputs.model_output,
        test_data=prep.outputs.test_data,
    )
    return {
        "trained_model": train.outputs.model_output,
        "metrics": evaluate.outputs.metrics_output,
    }


def main():
    raw_data_asset = ml_client.data.get(name="nsl-kdd-raw", version="1")

    pipeline_job = network_anomaly_pipeline(
        raw_data_input=Input(type=AssetTypes.URI_FOLDER, path=raw_data_asset.id)
    )

    submitted_job = ml_client.jobs.create_or_update(
        pipeline_job, experiment_name="network-anomaly-detection"
    )
    print(f"Pipeline submitted: {submitted_job.name}")
    print(f"Studio URL: {submitted_job.studio_url}")

    ml_client.jobs.stream(submitted_job.name)

    # ---- Conditional model registration ------------------------------
    completed_job = ml_client.jobs.get(submitted_job.name)
    if completed_job.status != "Completed":
        print(f"Pipeline did not complete successfully: {completed_job.status}")
        return

    metrics_path = ml_client.jobs.download(
        name=submitted_job.name, output_name="metrics", download_path="./outputs"
    )
    with open("./outputs/named-outputs/metrics/metrics.json") as f:
        metrics = json.load(f)

    print(f"Final metrics: {metrics}")

    if metrics["accuracy"] >= ACCURACY_THRESHOLD:
        print(f"Accuracy {metrics['accuracy']:.4f} >= {ACCURACY_THRESHOLD} — registering model")
        model = Model(
            path=f"azureml://jobs/{submitted_job.name}/outputs/trained_model/model.pkl",
            name="network-anomaly-detector",
            description="RandomForest classifier for NSL-KDD network intrusion detection",
            type=AssetTypes.CUSTOM_MODEL,
        )
        registered = ml_client.models.create_or_update(model)
        print(f"Registered model: {registered.name}, version {registered.version}")
    else:
        print(
            f"Accuracy {metrics['accuracy']:.4f} below threshold "
            f"{ACCURACY_THRESHOLD} — model NOT registered"
        )


if __name__ == "__main__":
    main()

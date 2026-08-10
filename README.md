# Azure ML Pipeline — Network Intrusion / Anomaly Detection

**Project 11** — a production-style ML pipeline built with **Azure Machine Learning SDK v2**
(`azure-ai-ml`), demonstrating data prep → training → evaluation → conditional model
registration, orchestrated as a reusable Azure ML pipeline running on an autoscaling
compute cluster.

> Note: Azure ML **SDK v1 reached end of support on June 30, 2026**. This project
> intentionally uses **SDK v2**, the current supported approach, instead of the
> `azureml.pipeline.steps` / `PythonScriptStep` pattern from the older docs.

## Use case

Binary classification on the **NSL-KDD** network intrusion detection dataset — a widely
used benchmark of ~125,000 labeled network connection records (normal vs. attack traffic).
The pipeline trains a classifier that flags anomalous/malicious connections from
connection-level features (duration, protocol, bytes transferred, error rates, etc.).

## Architecture

```
                 ┌────────────────────┐
  NSL-KDD raw ──►│   data_prep step   │──► train.csv / test.csv (OutputFileDatasetConfig)
                 └────────────────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │     train step     │──► model.pkl + mlflow run metrics
                 └────────────────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │   evaluate step    │──► metrics.json, registers model if
                 └────────────────────┘    accuracy ≥ threshold
```

Each step is an independent Azure ML **component** (own environment definition,
own compute), stitched together with the `@pipeline` DSL decorator — so any step
can be reused, versioned, or swapped independently.

## Repo structure

```
azure-ml-network-anomaly-pipeline/
├── README.md
├── requirements.txt
├── .gitignore
├── environment/
│   └── conda.yaml              # pipeline step environment (sklearn, pandas, mlflow)
├── src/
│   ├── data_prep/data_prep.py  # load, clean, encode, split NSL-KDD
│   ├── train/train.py          # train RandomForestClassifier, mlflow logging
│   └── evaluate/evaluate.py    # metrics + conditional model registration
├── pipeline.py                 # defines components + @pipeline, submits the run
├── setup/create_resources.sh   # az cli: resource group, workspace, compute cluster
└── setup/cleanup.sh            # az cli: teardown (avoid ongoing charges)
```

## Prerequisites

- Azure subscription (Azure ML free/paid tier is fine)
- Azure CLI installed and logged in (`az login`)
- Azure ML CLI extension: `az extension add -n ml`
- Python 3.10+, `pip install -r requirements.txt`
- NSL-KDD dataset files (`KDDTrain+.txt`, `KDDTest+.txt`) — download from the
  [Canadian Institute for Cybersecurity](https://www.unb.ca/cic/datasets/nsl.html)
  and place them in `data/`. Not committed to git (see `.gitignore`) — datasets don't
  belong in source control.

## Setup

Run one command at a time, verify output before proceeding (matches your usual workflow).

```bash
# 1. Log in and set subscription
az login
az account set --subscription "<your-subscription-id>"

# 2. Create resource group, ML workspace, and a scale-to-zero compute cluster
bash setup/create_resources.sh

# 3. Install Python dependencies locally (used to submit/monitor the pipeline)
pip install -r requirements.txt
```

`setup/create_resources.sh` creates:
- Resource group `rg-ml-network-anomaly`
- Azure ML workspace `mlw-network-anomaly`
- Compute cluster `cpu-cluster` (`Standard_DS3_v2`, min_nodes=0, max_nodes=2 — scales
  to zero when idle, so you're not billed while the cluster sits unused)

## Register the dataset

```bash
az ml data create --name nsl-kdd-raw --version 1 --type uri_folder --path ./data
```

## Run the pipeline

```bash
python pipeline.py
```

This submits the 3-step pipeline (`data_prep` → `train` → `evaluate`) to the
`cpu-cluster` compute target and prints a Studio URL to monitor progress live.

## Results

The `evaluate` step logs accuracy, precision, recall, F1, and ROC-AUC to the run via
MLflow, and only registers the model to the workspace model registry if accuracy meets
the threshold defined in `pipeline.py` (default `0.90`) — a basic quality gate before
anything becomes a "registered model" a downstream deployment could pick up.

## Cleanup

**Run this after every test/demo run** — matches the `terraform destroy` habit from the
AWS projects. Compute clusters with `min_nodes=0` don't bill while idle, but the
workspace, storage account, and container registry it provisions do.

```bash
bash setup/cleanup.sh
```

## What this demonstrates

- Azure ML SDK v2 component-based pipeline design (not the deprecated SDK v1 pattern)
- MLflow-native experiment tracking within Azure ML
- Autoscaling, cost-conscious compute (scale-to-zero cluster)
- A basic model quality gate before registration (no silent bad-model promotion)
- Reusable, independently versionable pipeline steps
- Applied to a security-relevant dataset (network intrusion detection) rather than a
  generic tutorial dataset

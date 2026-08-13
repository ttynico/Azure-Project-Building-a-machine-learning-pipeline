# Azure ML Pipeline — Network Intrusion / Anomaly Detection

**A production-style ML pipeline built with **Azure Machine Learning SDK v2**
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

## Troubleshooting notes (from actually building this)


**`az ml` CLI extension fails to install with `Cannot import 'maturin'`**
On some Windows Python setups, the Azure CLI's bundled Python (especially newer/32-bit
builds) has no prebuilt wheel available for one of the `ml` extension's dependencies,
and falls back to a source build that needs the Rust tool `maturin`, which isn't present.
Workaround used here: skip the `az ml` extension entirely and use the `azure-ai-ml`
Python SDK directly (see `setup/create_workspace.py` and `setup/register_dataset.py`)
for everything the extension would normally do — workspace creation, compute creation,
and data asset registration.

**`ModuleNotFoundError: No module named 'pkg_resources'` in the `train` step**
`mlflow` (via `mlflow.utils.requirements_utils`) imports `pkg_resources`, which comes
from `setuptools`, not the Python standard library. The base curated image didn't
guarantee a `setuptools` install, so `mlflow` failed on import inside the Azure ML
compute container. Simply adding `setuptools` to `environment/conda.yaml` wasn't
enough — an unpinned install resolved to a version that has since dropped
`pkg_resources`. Fix: pin `setuptools<81` explicitly.

**Lesson**: environment issues that only show up *inside the remote compute container*
(not locally) are a recurring Azure ML pain point — the fastest way to debug them is
Studio → Jobs → [failed run] → [failed step] → Outputs + logs → `user_logs/std_log.txt`,
which has the real Python traceback that the CLI's `jobs.stream()` output doesn't show.

## Optional: Real-time endpoint deployment

The registered model can also be deployed to a managed online endpoint for
real-time scoring, in addition to being consumable directly from the
pipeline's batch outputs.

> **Cost warning**: online endpoints run on an always-on VM and bill
> hourly regardless of traffic (~$70-140/mo for a small instance). Deploy,
> test, and delete in the same session — don't leave one running.

```bash
python setup/deploy_endpoint.py    # stand up the endpoint (several minutes)
python setup/test_endpoint.py      # send a real NSL-KDD test record, see predictions
python setup/delete_endpoint.py    # tear down immediately after testing
```

`deploy_endpoint.py` deploys the latest registered model version to a new
endpoint with a randomly generated name, saved locally to
`.last_endpoint_name` so the test/delete scripts don't need it retyped.

### Deployment troubleshooting notes

Getting a working online endpoint took five iterations. In order:

1. **`ModuleNotFoundError: No module named 'pkg_resources'`** — same root
   cause as the training-step fix above (missing `setuptools`), but this
   surfaces again here because online endpoints build their own container
   image from the environment spec, independent of the training image.

2. **`azureml-inference-server-http` missing** — training environments and
   inference (serving) environments have different requirements. The
   training `conda.yaml` has no reason to include the inference server
   package, but a deployment does. Fix: created a separate
   `environment/conda-inference.yaml` with only what serving needs
   (scikit-learn, pandas, joblib, azureml-inference-server-http) — no
   mlflow, no training-only dependencies.

3. **Training base image used for inference** — `mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu22.04`
   is meant for training/job containers, not serving. Switched to
   `mcr.microsoft.com/azureml/minimal-ubuntu22.04-py39-cpu-inference:latest`,
   Microsoft's inference-specific base image, which already has the
   inference server's dependencies correctly resolved.

4. **Model registered pointing at a single file, not its folder** — the
   original `Model(path=".../outputs/trained_model/model.pkl")` only
   pulled `model.pkl` into the registered asset, silently dropping
   `feature_columns.txt` that `score.py` also needs. Fixed by pointing
   `path` at the `trained_model` output folder instead of the file inside
   it, in both `pipeline.py` (for future runs) and via a one-off
   re-registration for the existing job.

5. **`score.py` assumed a fixed path depth** — once the model folder
   *was* registered correctly, Azure ML preserved its internal folder
   structure (`<model_dir>/model_output/model.pkl`), which didn't match
   `score.py`'s assumption that `model.pkl` sat directly in
   `AZUREML_MODEL_DIR`. Fixed by walking the model directory to locate
   the files instead of hardcoding a path depth — more robust to however
   Azure ML happens to nest the registered asset.

**Lesson**: online endpoint failures fall into two log locations depending
on *when* the container dies. If it crashes before the liveness probe
starts, `ml_client.online_deployments.begin_create_or_update(...)` raises
directly with a short reason (e.g. `BadArgument: User container has
crashed or terminated`). If it starts but then fails (as in issues 4-5
above), the SDK error is a generic `502` liveness probe failure with no
detail — the actual Python traceback only shows up via
`ml_client.online_deployments.get_logs(name=..., endpoint_name=...)`,
which should be the first move on any online endpoint failure, not the
last.

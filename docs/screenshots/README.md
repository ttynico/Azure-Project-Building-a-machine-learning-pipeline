# Screenshots

A visual record of the project working end to end in Azure - resource
provisioning, pipeline execution, model registration, and endpoint
deployment/testing.

## Resource provisioning

| File | Shows |
|---|---|
| `resource-group-1.png`, `resource-group-2.png`, `resource-group-3.png` | Resource group `rg-ml-network-anomaly` confirmed in the Azure Portal, activity log |
| `all-resource-group.png` | Full resource group contents: workspace, storage, key vault, Log Analytics, App Insights |
| `studio.png` - `studio___.png` | Azure ML workspace overview and Studio landing page |

## Data

| File | Shows |
|---|---|
| `data.png` | `nsl-kdd-raw` data asset registered in Studio -> Data |

## Pipeline execution

| File | Shows |
|---|---|
| `pipeline.png` - `pipeline_______.png` | Pipeline job history (failed -> failed -> completed) and the full DAG (data_prep -> train -> evaluate) with output artifacts |

## Compute

| File | Shows |
|---|---|
| `compute.png` | `cpu-cluster` compute cluster, node scaling |

## Model

| File | Shows |
|---|---|

| `train-model-1.png`, `train-model-2.png` | Train step job details, git commit linkage, and `std_log.txt` showing successful training after the `setuptools`/`pkg_resources` fix |
| `models.png`, `models_.png` | Registered model `network-anomaly-detector` in the model registry |

## Online endpoint deployment

| File | Shows |
|---|---|
| `endpoints.png` - `endpoints________.png` | Endpoint creation attempts (including failed ones - `az ml` extension issues, missing inference package, model path bugs), the eventual successful deployment (`blue`, 100% traffic, Succeeded), the Test tab, and clean container logs (`ContainerReady`, no ARM errors) |

---

The failed-attempt screenshots are included deliberately - they're part
of the real debugging story documented in the main [README](../../README.md#deployment-troubleshooting-notes),
not just the polished end state.

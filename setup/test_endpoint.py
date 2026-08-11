"""
Sends a sample scoring request to the deployed online endpoint using a
real record from the NSL-KDD test set, so the response is meaningful
(not just structurally valid).

Usage:
    python setup/test_endpoint.py
"""
import json
import os

import pandas as pd

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential

SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID", "bcf47805-ae92-4706-8cf2-13bdb2fe29ba")
RESOURCE_GROUP = os.environ.get("AZURE_RESOURCE_GROUP", "rg-ml-network-anomaly")
WORKSPACE_NAME = os.environ.get("AZURE_ML_WORKSPACE", "mlw-network-anomaly")


def load_endpoint_name():

    with open(".last_endpoint_name") as f:
        return f.read().strip()


def build_sample_request():
    column_names = [
        "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes",
        "land", "wrong_fragment", "urgent", "hot", "num_failed_logins",
        "logged_in", "num_compromised", "root_shell", "su_attempted",
        "num_root", "num_file_creations", "num_shells", "num_access_files",
        "num_outbound_cmds", "is_host_login", "is_guest_login", "count",
        "srv_count", "serror_rate", "srv_serror_rate", "rerror_rate",
        "srv_rerror_rate", "same_srv_rate", "diff_srv_rate", "srv_diff_host_rate",
        "dst_host_count", "dst_host_srv_count", "dst_host_same_srv_rate",
        "dst_host_diff_srv_rate", "dst_host_same_src_port_rate",
        "dst_host_srv_diff_host_rate", "dst_host_serror_rate",
        "dst_host_srv_serror_rate", "dst_host_rerror_rate",
        "dst_host_srv_rerror_rate", "label", "difficulty",
    ]
    df = pd.read_csv("data/KDDTest+.txt", header=None, names=column_names, nrows=5)
    true_labels = (df["label"].str.strip() != "normal").astype(int).tolist()
    df = df.drop(columns=["label", "difficulty"])
    df = pd.get_dummies(df, columns=["protocol_type", "service", "flag"])

    records = df.to_dict(orient="records")
    return records, true_labels


def main():
    ml_client = MLClient(
        DefaultAzureCredential(),
        subscription_id=SUBSCRIPTION_ID,
        resource_group_name=RESOURCE_GROUP,
        workspace_name=WORKSPACE_NAME,
    )

    endpoint_name = load_endpoint_name()
    records, true_labels = build_sample_request()

    request_body = json.dumps({"data": records})
    with open("sample_request.json", "w") as f:
        f.write(request_body)

    print(f"Sending {len(records)} test records to endpoint '{endpoint_name}'...")
    response = ml_client.online_endpoints.invoke(
        endpoint_name=endpoint_name,
        request_file="sample_request.json",
    )

    result = json.loads(response)
    print("\nResponse:")
    print(json.dumps(result, indent=2))

    print("\nTrue labels (0=normal, 1=attack):", true_labels)


if __name__ == "__main__":
    main()

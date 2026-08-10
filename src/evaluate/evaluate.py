"""
Evaluation step for the network anomaly detection pipeline.

Loads the trained model, scores it against the held-out test split, logs
metrics via MLflow, and writes a metrics.json artifact. Registration to the
Azure ML model registry is handled in pipeline.py based on the accuracy
threshold, using this step's metrics output — keeping the quality gate in
one visible place rather than buried in a script.
"""
import argparse
import json
import os

import joblib
import mlflow
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_input", type=str, required=True)
    parser.add_argument("--test_data", type=str, required=True)
    parser.add_argument("--metrics_output", type=str, required=True)
    return parser.parse_args()


def main():
    args = parse_args()

    model = joblib.load(os.path.join(args.model_input, "model.pkl"))
    with open(os.path.join(args.model_input, "feature_columns.txt")) as f:
        feature_columns = f.read().splitlines()

    test_df = pd.read_csv(os.path.join(args.test_data, "test.csv"))
    y_test = test_df["label"]
    X_test = test_df.drop(columns=["label"])

    # Align test columns to the training feature set (one-hot encoding can
    # produce columns present in train but absent in test, or vice versa).
    X_test = X_test.reindex(columns=feature_columns, fill_value=0)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1": f1_score(y_test, y_pred),
        "roc_auc": roc_auc_score(y_test, y_proba),
    }

    for name, value in metrics.items():
        mlflow.log_metric(name, value)
        print(f"{name}: {value:.4f}")

    os.makedirs(args.metrics_output, exist_ok=True)
    with open(os.path.join(args.metrics_output, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)


if __name__ == "__main__":
    main()

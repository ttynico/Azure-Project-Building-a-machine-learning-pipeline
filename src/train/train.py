"""
Training step for the network anomaly detection pipeline.

Trains a RandomForestClassifier on the prepped NSL-KDD training split.
Uses MLflow autologging (Azure ML's native experiment tracking) so params,
metrics, and the model artifact are captured on the run automatically.
"""
import argparse
import os

import joblib
import mlflow
import pandas as pd
from sklearn.ensemble import RandomForestClassifier


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_data", type=str, required=True)
    parser.add_argument("--model_output", type=str, required=True)
    parser.add_argument("--n_estimators", type=int, default=200)
    parser.add_argument("--max_depth", type=int, default=20)
    return parser.parse_args()


def main():
    args = parse_args()
    mlflow.sklearn.autolog()

    train_path = os.path.join(args.train_data, "train.csv")
    df = pd.read_csv(train_path)
    X = df.drop(columns=["label"])
    y = df["label"]

    print(f"Training on {len(X)} rows, {X.shape[1]} features")
    print(f"n_estimators={args.n_estimators}, max_depth={args.max_depth}")

    model = RandomForestClassifier(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        n_jobs=-1,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X, y)

    os.makedirs(args.model_output, exist_ok=True)
    model_path = os.path.join(args.model_output, "model.pkl")
    joblib.dump(model, model_path)
    # Also persist the feature column order — the evaluate step needs it to
    # align the test set columns after one-hot encoding.
    with open(os.path.join(args.model_output, "feature_columns.txt"), "w") as f:
        f.write("\n".join(X.columns))

    print(f"Model saved to {model_path}")


if __name__ == "__main__":
    main()

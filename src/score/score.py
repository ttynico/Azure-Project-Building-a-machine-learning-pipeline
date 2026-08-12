"""
Entry script for the managed online endpoint.

Loads the trained RandomForest model (and its feature column order) once at
container startup, then scores incoming requests. Azure ML's inference
server calls init() on startup and run() per request.
"""
import json
import os

import joblib
import pandas as pd


def init():
    global model, feature_columns

    model_dir = os.environ["AZUREML_MODEL_DIR"]

    # The registered model asset preserves the training output folder
    # structure, so the actual files can be nested (e.g.
    # <model_dir>/model_output/model.pkl) rather than sitting directly in
    # model_dir. Search for them instead of assuming a fixed depth.
    model_path = None
    columns_path = None
    for root, _, files in os.walk(model_dir):
        if "model.pkl" in files:
            model_path = os.path.join(root, "model.pkl")
        if "feature_columns.txt" in files:
            columns_path = os.path.join(root, "feature_columns.txt")

    if model_path is None or columns_path is None:
        raise FileNotFoundError(
            f"Could not find model.pkl and/or feature_columns.txt under {model_dir}"
        )

    model = joblib.load(model_path)
    with open(columns_path) as f:
        feature_columns = f.read().splitlines()

    print(f"Model loaded from {model_path}. Expecting {len(feature_columns)} features.")


def run(raw_data):
    """
    Expects JSON: {"data": [{"duration": 0, "src_bytes": 491, ...}, ...]}
    Each dict is one connection record with the same (already one-hot
    encoded) feature names produced by data_prep.py. Returns a prediction
    (0=normal, 1=attack) and attack probability per record.
    """
    try:
        payload = json.loads(raw_data)
        records = payload["data"]

        df = pd.DataFrame(records)
        df = df.reindex(columns=feature_columns, fill_value=0)

        predictions = model.predict(df)
        probabilities = model.predict_proba(df)[:, 1]

        results = [
            {"prediction": int(pred), "attack_probability": float(prob)}
            for pred, prob in zip(predictions, probabilities)
        ]
        return {"results": results}

    except Exception as e:
        return {"error": str(e)}

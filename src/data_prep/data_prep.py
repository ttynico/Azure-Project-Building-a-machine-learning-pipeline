"""
Data preparation step for the network anomaly detection pipeline.

Reads raw NSL-KDD connection records, assigns the standard 41 feature columns
+ label, one-hot encodes the categorical protocol/service/flag columns,
collapses the multi-class attack label into binary (normal=0 / attack=1),
and writes a train/test split as CSV to the step's output paths.
"""
import argparse
import os

import pandas as pd
from sklearn.model_selection import train_test_split

# Standard NSL-KDD column names (41 features + label + difficulty score).
# The raw files ship with no header row.
COLUMN_NAMES = [
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

CATEGORICAL_COLS = ["protocol_type", "service", "flag"]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw_data", type=str, required=True,
                         help="Path to folder containing KDDTrain+.txt")
    parser.add_argument("--train_output", type=str, required=True)
    parser.add_argument("--test_output", type=str, required=True)
    parser.add_argument("--test_size", type=float, default=0.2)
    return parser.parse_args()


def load_raw(raw_data_dir: str) -> pd.DataFrame:
    train_path = os.path.join(raw_data_dir, "KDDTrain+.txt")
    df = pd.read_csv(train_path, header=None, names=COLUMN_NAMES)
    return df


def clean_and_encode(df: pd.DataFrame) -> pd.DataFrame:
    # Binary label: 'normal' -> 0, anything else (attack type) -> 1
    df["label"] = (df["label"].str.strip() != "normal").astype(int)
    df = df.drop(columns=["difficulty"])

    # One-hot encode categorical connection attributes
    df = pd.get_dummies(df, columns=CATEGORICAL_COLS)
    return df


def main():
    args = parse_args()

    print(f"Loading raw data from {args.raw_data}")
    df = load_raw(args.raw_data)
    print(f"Loaded {len(df)} records")

    df = clean_and_encode(df)
    print(f"After encoding: {df.shape[1]} columns")

    train_df, test_df = train_test_split(
        df, test_size=args.test_size, random_state=42, stratify=df["label"]
    )
    print(f"Train: {len(train_df)} rows | Test: {len(test_df)} rows")
    print(f"Attack rate — train: {train_df['label'].mean():.3f}, "
          f"test: {test_df['label'].mean():.3f}")

    os.makedirs(args.train_output, exist_ok=True)
    os.makedirs(args.test_output, exist_ok=True)
    train_df.to_csv(os.path.join(args.train_output, "train.csv"), index=False)
    test_df.to_csv(os.path.join(args.test_output, "test.csv"), index=False)


if __name__ == "__main__":
    main()

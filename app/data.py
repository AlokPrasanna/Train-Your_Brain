import os

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from config import Config


# ---------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------
def load_dataframe(path: str | None = None) -> pd.DataFrame:
  
    path = path or Config.DATASET_PATH

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Dataset not found at '{path}'.\n"
            "Download the official UCI Banknote Authentication dataset:\n"
            "  https://archive.ics.uci.edu/dataset/267/banknote+authentication\n"
            f"Save the file exactly as '{path}' (do NOT rename it to .csv)."
        )

    columns = Config.FEATURE_COLUMNS + [Config.TARGET_COLUMN]
    df = pd.read_csv(path, header=None, names=columns)

    if df.shape[1] != 5:
        raise ValueError(
            f"Expected 5 columns, got {df.shape[1]}. "
            "Is this really the Banknote Authentication file?"
        )
    if df.isnull().any().any():
        raise ValueError("Dataset contains missing values.")
    if not set(df[Config.TARGET_COLUMN].unique()).issubset({0, 1}):
        raise ValueError("Target column must contain only 0 and 1.")

    return df


def dataset_info(path: str | None = None) -> dict:
    df = load_dataframe(path)
    target = df[Config.TARGET_COLUMN]

    return {
        "path": path or Config.DATASET_PATH,
        "rows": int(df.shape[0]),
        "features": Config.FEATURE_COLUMNS,
        "target": Config.TARGET_COLUMN,
        "class_distribution": {
            "class_0": int((target == 0).sum()),
            "class_1": int((target == 1).sum()),
        },
        "preview": df.head(5).to_dict(orient="records"),
    }


# ---------------------------------------------------------------------
# Splitting
# ---------------------------------------------------------------------
def parse_split_ratio(split_ratio: str) -> float:
   
    if split_ratio not in Config.ALLOWED_SPLIT_RATIOS:
        raise ValueError(
            f"Invalid split_ratio '{split_ratio}'. "
            f"Allowed: {Config.ALLOWED_SPLIT_RATIOS}"
        )
    train_part, _test_part = split_ratio.split(":")
    return int(train_part) / 100.0


def prepare_datasets(split_ratio: str = None):
    
    split_ratio = split_ratio or Config.DEFAULT_SPLIT_RATIO
    train_fraction = parse_split_ratio(split_ratio)  

    df = load_dataframe()
    X = df[Config.FEATURE_COLUMNS].to_numpy(dtype=np.float32)
    y = df[Config.TARGET_COLUMN].to_numpy(dtype=np.float32)

    # --- Step 2: train+val vs test -----------------------------------
    # test_size is the *test* portion of the full dataset.
    test_fraction = 1.0 - train_fraction
    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y,
        test_size=test_fraction,
        random_state=Config.RANDOM_SEED,
        stratify=y,
    )

    # --- Step 3: train vs val ----------------------------------------
    # Carve validation out of the train+val portion.
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval,
        test_size=Config.VALIDATION_FRACTION,
        random_state=Config.RANDOM_SEED,
        stratify=y_trainval,
    )

    # --- Step 4: scale (fit on train only!) --------------------------
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)   # fit + transform
    X_val = scaler.transform(X_val)           # transform only
    X_test = scaler.transform(X_test)         # transform only

    total = len(y)
    split_summary = {
        "split_ratio": split_ratio,
        "total_rows": int(total),
        "train_rows": int(len(y_train)),
        "val_rows": int(len(y_val)),
        "test_rows": int(len(y_test)),
        "train_fraction": round(len(y_train) / total, 4),
        "val_fraction": round(len(y_val) / total, 4),
        "test_fraction": round(len(y_test) / total, 4),
        "validation_fraction_of_trainval": Config.VALIDATION_FRACTION,
        "random_seed": Config.RANDOM_SEED,
    }

    return {
        "X_train": X_train, "y_train": y_train,
        "X_val": X_val,     "y_val": y_val,
        "X_test": X_test,   "y_test": y_test,
        "feature_names": Config.FEATURE_COLUMNS,
        "split_summary": split_summary,
        "scaler": scaler,
    }
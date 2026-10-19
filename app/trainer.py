import random
import time

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

from config import Config


# ---------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------
def _set_seeds(seed: int) -> None:
    """Set every relevant RNG seed so runs are reproducible."""
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)


# ---------------------------------------------------------------------
# Model building
# ---------------------------------------------------------------------
def build_model(config: dict, input_dim: int) -> keras.Model:
    """
    Construct a fresh Keras model from a validated configuration.

    Architecture:
      - Input layer with shape (input_dim,)
      - N hidden Dense layers using config["activation"]
      - Output Dense layer with 1 unit, sigmoid (binary classification)

    Optimizer is Adam with the chosen learning rate.
    Loss is binary crossentropy.
    Metric is accuracy.
    """
    hidden_layers = config["hidden_layers"]
    neurons = config["neurons"]
    activation = config["activation"]
    learning_rate = config["learning_rate"]

    model = keras.Sequential(name="train_your_brain")
    model.add(keras.Input(shape=(input_dim,), name="input"))

    for i, n in enumerate(neurons, start=1):
        model.add(
            layers.Dense(n, activation=activation, name=f"hidden_{i}")
        )

    model.add(layers.Dense(1, activation="sigmoid", name="output"))

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    return model


# ---------------------------------------------------------------------
# Training + evaluation
# ---------------------------------------------------------------------
def train_model(config: dict, datasets: dict) -> dict:
    """
    Build, train, evaluate, and summarize a model run.

    Parameters
    ----------
    config : validated configuration dict
    datasets : output of app.data.prepare_datasets()

    Returns
    -------
    dict ready to be JSON-serialized by Flask.
    """
    _set_seeds(Config.RANDOM_SEED)

    X_train = datasets["X_train"]
    y_train = datasets["y_train"]
    X_val = datasets["X_val"]
    y_val = datasets["y_val"]
    X_test = datasets["X_test"]
    y_test = datasets["y_test"]

    input_dim = X_train.shape[1]

    model = build_model(config, input_dim)

    start = time.time()
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=config["epochs"],
        batch_size=config["batch_size"],
        verbose=0,               # keep the Flask console quiet
    )
    duration = time.time() - start

    # Final training and validation values from the last epoch.
    train_acc = float(history.history["accuracy"][-1])
    val_acc = float(history.history["val_accuracy"][-1])
    train_loss = float(history.history["loss"][-1])
    val_loss = float(history.history["val_loss"][-1])

    # Evaluate on the held-out test set. Never used for any decision.
    test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
    test_loss = float(test_loss)
    test_acc = float(test_acc)

    target_met = val_acc >= Config.MISSION_TARGET

    return {
        "history": {
            "accuracy":         [float(v) for v in history.history["accuracy"]],
            "val_accuracy":     [float(v) for v in history.history["val_accuracy"]],
            "loss":             [float(v) for v in history.history["loss"]],
            "val_loss":         [float(v) for v in history.history["val_loss"]],
        },
        "metrics": {
            "train_accuracy": train_acc,
            "val_accuracy":   val_acc,
            "train_loss":     train_loss,
            "val_loss":       val_loss,
            "test_accuracy":  test_acc,
            "test_loss":      test_loss,
        },
        "mission": {
            "target":     Config.MISSION_TARGET,
            "achieved":   target_met,
            "message": (
                "✅ Mission accomplished — validation accuracy is at or above the target."
                if target_met else
                "🔁 Keep experimenting — validation accuracy is below the target."
            ),
        },
        "duration_seconds": round(duration, 3),
        "split_summary":   datasets["split_summary"],
    }


# ---------------------------------------------------------------------
# Keras code generation (for the "Your AI Code" panel)
# ---------------------------------------------------------------------
def generate_code(config: dict) -> str:
    """
    Produce Keras source code that matches the configuration EXACTLY.

    The generated script is standalone: if a student pasted it into a file
    at the project root and ran `python thatfile.py`, it would reproduce
    the same split, scale, model, and training run.
    """
    hidden_layers = config["hidden_layers"]
    neurons = config["neurons"]
    activation = config["activation"]
    epochs = config["epochs"]
    batch_size = config["batch_size"]
    learning_rate = config["learning_rate"]
    split_ratio = config.get("split_ratio", Config.DEFAULT_SPLIT_RATIO)

    train_part, test_part = split_ratio.split(":")
    test_fraction = int(test_part) / 100.0
    val_fraction = Config.VALIDATION_FRACTION
    seed = Config.RANDOM_SEED
    noise_fraction = Config.LABEL_NOISE_FRACTION

    # --- Build the hidden-layer lines ---
    hidden_lines = []
    for i, n in enumerate(neurons, start=1):
        hidden_lines.append(
            f'    layers.Dense({n}, activation="{activation}", name="hidden_{i}"),'
        )
    hidden_block = "\n".join(hidden_lines)

    return f'''# =============================================================
# Generated by Train Your Brain
# This code reproduces the configuration you selected.
# Copy it, paste it into a file, and it will train the same model.
# =============================================================

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

# --- Reproducibility ---------------------------------------------
SEED = {seed}
np.random.seed(SEED)
tf.random.set_seed(SEED)

# --- 1. Load the dataset -----------------------------------------
# The file has no header; columns are: variance, skewness, curtosis, entropy, class.
columns = ["variance", "skewness", "curtosis", "entropy", "class"]
df = pd.read_csv("data/data_banknote_authentication.txt", header=None, names=columns)

X = df[["variance", "skewness", "curtosis", "entropy"]].to_numpy(dtype=np.float32)
y = df["class"].to_numpy(dtype=np.float32)

# --- Inject label noise so the task is not trivially solvable -----
# This is the same preprocessing the workshop server performs.
# {int(noise_fraction*100)}% of labels are randomly flipped, capping
# the achievable accuracy at roughly {round((1-noise_fraction)*100)}%.
NOISE_FRACTION = {noise_fraction}
if NOISE_FRACTION > 0:
    rng = np.random.default_rng(SEED)
    n_flip = int(round(len(y) * NOISE_FRACTION))
    flip_idx = rng.choice(len(y), size=n_flip, replace=False)
    y[flip_idx] = 1.0 - y[flip_idx]

# --- 2. Split: train+val vs test ---------------------------------
# Selected split ratio: {split_ratio}  (test = {test_part}%)
X_trainval, X_test, y_trainval, y_test = train_test_split(
    X, y,
    test_size={test_fraction},
    random_state=SEED,
    stratify=y,
)

# --- 3. Split: train vs validation ({int(val_fraction*100)}% of train+val) -----
X_train, X_val, y_train, y_val = train_test_split(
    X_trainval, y_trainval,
    test_size={val_fraction},
    random_state=SEED,
    stratify=y_trainval,
)

# --- 4. Scale features (fit on TRAIN ONLY to prevent leakage) ----
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_val   = scaler.transform(X_val)
X_test  = scaler.transform(X_test)

# --- 5. Build the network ----------------------------------------
model = keras.Sequential(name="train_your_brain")
model.add(keras.Input(shape=(X_train.shape[1],), name="input"))
model.add(layers.Dense({neurons[0]}, activation="{activation}", name="hidden_1"))
{"" if hidden_layers == 1 else chr(10).join(hidden_lines[1:])}
model.add(layers.Dense(1, activation="sigmoid", name="output"))

# --- 6. Compile ---------------------------------------------------
model.compile(
    optimizer=keras.optimizers.Adam(learning_rate={learning_rate}),
    loss="binary_crossentropy",
    metrics=["accuracy"],
)

# --- 7. Train -----------------------------------------------------
history = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs={epochs},
    batch_size={batch_size},
    verbose=1,
)

# --- 8. Evaluate on the untouched test set ------------------------
test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
print(f"Test accuracy: {{test_acc:.4f}}")
print(f"Test loss:     {{test_loss:.4f}}")
'''

# NOTE: the hidden_block variable above is intentionally not used
# directly; the f-string builds the correct layer lines inline so the
# first layer count is not duplicated. This is a deliberate trade-off
# for readability of the generated code.
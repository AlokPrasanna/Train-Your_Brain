from config import Config


# ---------------------------------------------------------------------
# Pricing table (single source of truth)
# ---------------------------------------------------------------------
BASE_COST = 5                     # any training run pays this
COST_PER_HIDDEN_LAYER = 3         # flat, per hidden layer

# Cost per layer, depends on how many neurons that layer has.
NEURON_COST = {
    4: 2,
    8: 4,
    16: 6,
    32: 10,
}

ACTIVATION_COST = {
    "relu": 0,
    "tanh": 2,
    "sigmoid": 3,
}

# Smaller batches = more gradient updates per epoch = more compute.
BATCH_COST = {
    8: 4,
    16: 3,
    32: 1,
    64: 0,
}

# Very small learning rates need more epochs to converge, so they
# are treated as costing slightly more.
LEARNING_RATE_COST = {
    0.01: 0,
    0.001: 1,
    0.0001: 3,
}

COST_PER_10_EPOCHS = 1            # 10 -> 1, 25 -> 2, 50 -> 5, 75 -> 7, 100 -> 10


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------
def _epoch_cost(epochs: int) -> int:
    """Round up to the nearest 10-epoch block. 25 -> 3? No: 25 -> 2 (ceil(25/10))."""
    # We charge per *started* block of 10 epochs. 25 -> 3, 50 -> 5, 100 -> 10.
    # Actually: use integer ceiling so 25 costs the same as 30.
    return (epochs + 9) // 10


def calculate_cost(config: dict) -> dict:
  
    hidden_layers = config["hidden_layers"]
    neurons = config["neurons"]
    activation = config["activation"]
    epochs = config["epochs"]
    batch_size = config["batch_size"]
    learning_rate = config["learning_rate"]
    split_ratio = config.get("split_ratio", Config.DEFAULT_SPLIT_RATIO)

    breakdown = []

    # --- Base ---------------------------------------------------------
    breakdown.append({
        "label": "Base training cost",
        "coins": BASE_COST,
        "detail": "Charged once for any training run.",
    })

    # --- Hidden layers -------------------------------------------------
    layer_cost = COST_PER_HIDDEN_LAYER * hidden_layers
    breakdown.append({
        "label": f"Hidden layers ({hidden_layers} × {COST_PER_HIDDEN_LAYER})",
        "coins": layer_cost,
        "detail": "Flat cost per hidden layer.",
    })

    # --- Neurons (per layer) ------------------------------------------
    neurons_total = 0
    for i, n in enumerate(neurons, start=1):
        c = NEURON_COST[n]
        neurons_total += c
        breakdown.append({
            "label": f"Layer {i}: {n} neurons",
            "coins": c,
            "detail": f"{n}-neuron layer price.",
        })

    # --- Activation function ------------------------------------------
    act_cost = ACTIVATION_COST[activation]
    breakdown.append({
        "label": f"Activation: {activation}",
        "coins": act_cost,
        "detail": "ReLU is free; tanh and sigmoid cost more.",
    })

    # --- Epochs -------------------------------------------------------
    epoch_cost = _epoch_cost(epochs) * COST_PER_10_EPOCHS
    breakdown.append({
        "label": f"Epochs: {epochs}",
        "coins": epoch_cost,
        "detail": f"{COST_PER_10_EPOCHS} coin per started block of 10 epochs.",
    })

    # --- Batch size ---------------------------------------------------
    batch_cost = BATCH_COST[batch_size]
    breakdown.append({
        "label": f"Batch size: {batch_size}",
        "coins": batch_cost,
        "detail": "Smaller batches mean more updates per epoch.",
    })

    # --- Learning rate ------------------------------------------------
    lr_cost = LEARNING_RATE_COST[learning_rate]
    breakdown.append({
        "label": f"Learning rate: {learning_rate}",
        "coins": lr_cost,
        "detail": "Very small LRs need more epochs to converge.",
    })

    # --- Data split (explicitly FREE) ---------------------------------
    breakdown.append({
        "label": f"Data split: {split_ratio}",
        "coins": 0,
        "detail": "Split choice changes your data, not your compute bill.",
    })

    total = sum(item["coins"] for item in breakdown)

    return {
        "total": total,
        "breakdown": breakdown,
    }
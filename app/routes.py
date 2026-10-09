from flask import Blueprint, jsonify, render_template, request, current_app

from app.cost import calculate_cost
from app.data import dataset_info, prepare_datasets
from app.trainer import generate_code, train_model
from config import Config


bp = Blueprint("main", __name__)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _error(message: str, status: int = 400):
    """Consistent error response."""
    return jsonify({"ok": False, "error": message}), status


def _validate_config(payload: dict):
    """
    Validate a configuration payload sent from the browser.

    Returns
    -------
    (config, None) on success
    (None, error_message) on failure
    """
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object."

    required = [
        "hidden_layers", "neurons", "activation",
        "epochs", "batch_size", "learning_rate", "split_ratio",
    ]
    for key in required:
        if key not in payload:
            return None, f"Missing field: {key}"

    # --- hidden_layers ------------------------------------------------
    try:
        hidden_layers = int(payload["hidden_layers"])
    except (TypeError, ValueError):
        return None, "hidden_layers must be an integer."
    if hidden_layers not in Config.ALLOWED_HIDDEN_LAYERS:
        return None, f"hidden_layers must be one of {Config.ALLOWED_HIDDEN_LAYERS}."

    # --- neurons ------------------------------------------------------
    neurons = payload["neurons"]
    if not isinstance(neurons, list):
        return None, "neurons must be a list of integers."
    if len(neurons) != hidden_layers:
        return None, (
            f"neurons must contain exactly {hidden_layers} values "
            f"(one per hidden layer)."
        )
    try:
        neurons = [int(n) for n in neurons]
    except (TypeError, ValueError):
        return None, "Every neuron count must be an integer."
    for n in neurons:
        if n not in Config.ALLOWED_NEURONS:
            return None, f"Each neuron count must be one of {Config.ALLOWED_NEURONS}."

    # --- activation ---------------------------------------------------
    activation = payload["activation"]
    if activation not in Config.ALLOWED_ACTIVATIONS:
        return None, f"activation must be one of {Config.ALLOWED_ACTIVATIONS}."

    # --- epochs -------------------------------------------------------
    try:
        epochs = int(payload["epochs"])
    except (TypeError, ValueError):
        return None, "epochs must be an integer."
    if epochs not in Config.ALLOWED_EPOCHS:
        return None, f"epochs must be one of {Config.ALLOWED_EPOCHS}."

    # --- batch_size ---------------------------------------------------
    try:
        batch_size = int(payload["batch_size"])
    except (TypeError, ValueError):
        return None, "batch_size must be an integer."
    if batch_size not in Config.ALLOWED_BATCH_SIZES:
        return None, f"batch_size must be one of {Config.ALLOWED_BATCH_SIZES}."

    # --- learning_rate ------------------------------------------------
    try:
        learning_rate = float(payload["learning_rate"])
    except (TypeError, ValueError):
        return None, "learning_rate must be a number."
    # Float equality is unreliable — compare with tolerance.
    if not any(abs(learning_rate - r) < 1e-12 for r in Config.ALLOWED_LEARNING_RATES):
        return None, f"learning_rate must be one of {Config.ALLOWED_LEARNING_RATES}."

    # --- split_ratio --------------------------------------------------
    split_ratio = payload["split_ratio"]
    if split_ratio not in Config.ALLOWED_SPLIT_RATIOS:
        return None, f"split_ratio must be one of {Config.ALLOWED_SPLIT_RATIOS}."

    return {
        "hidden_layers": hidden_layers,
        "neurons": neurons,
        "activation": activation,
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "split_ratio": split_ratio,
    }, None


# ---------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------
@bp.get("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------
# /api/config
# ---------------------------------------------------------------------
@bp.get("/api/config")
def api_config():
    return jsonify({
        "ok": True,
        "allowed": {
            "hidden_layers": Config.ALLOWED_HIDDEN_LAYERS,
            "neurons": Config.ALLOWED_NEURONS,
            "activations": Config.ALLOWED_ACTIVATIONS,
            "epochs": Config.ALLOWED_EPOCHS,
            "batch_sizes": Config.ALLOWED_BATCH_SIZES,
            "learning_rates": Config.ALLOWED_LEARNING_RATES,
            "split_ratios": Config.ALLOWED_SPLIT_RATIOS,
        },
        "defaults": {
            "hidden_layers": 2,
            "neurons": [16, 16],
            "activation": "relu",
            "epochs": 50,
            "batch_size": 32,
            "learning_rate": 0.001,
            "split_ratio": Config.DEFAULT_SPLIT_RATIO,
        },
        "initial_coins": Config.INITIAL_COINS,
        "mission_target": Config.MISSION_TARGET,
        "validation_fraction": Config.VALIDATION_FRACTION,
        "random_seed": Config.RANDOM_SEED,
    })


# ---------------------------------------------------------------------
# /api/dataset
# ---------------------------------------------------------------------
@bp.get("/api/dataset")
def api_dataset():
    try:
        return jsonify({"ok": True, "dataset": dataset_info()})
    except FileNotFoundError as exc:
        return _error(str(exc), status=500)
    except Exception as exc:
        current_app.logger.exception("Failed to load dataset info")
        return _error("Could not load dataset information.", status=500)


# ---------------------------------------------------------------------
# /api/cost
# ---------------------------------------------------------------------
@bp.post("/api/cost")
def api_cost():
    payload = request.get_json(silent=True)
    if payload is None:
        return _error("Body must be valid JSON.", status=400)

    config, err = _validate_config(payload)
    if err:
        return _error(err, status=400)

    try:
        cost = calculate_cost(config)
    except Exception:
        current_app.logger.exception("Cost calculation failed")
        return _error("Could not calculate cost for that configuration.", status=500)

    return jsonify({
        "ok": True,
        "cost": cost,
        "code": generate_code(config),
        "config": config,
    })


# ---------------------------------------------------------------------
# /api/train
# ---------------------------------------------------------------------
@bp.post("/api/train")
def api_train():
    payload = request.get_json(silent=True)
    if payload is None:
        return _error("Body must be valid JSON.", status=400)

    config, err = _validate_config(payload)
    if err:
        return _error(err, status=400)

    # --- Affordability check -----------------------------------------
    try:
        claimed_balance = int(payload.get("balance", -1))
    except (TypeError, ValueError):
        return _error("balance must be an integer.", status=400)
    if claimed_balance < 0:
        return _error("balance is missing or invalid.", status=400)

    cost = calculate_cost(config)
    if claimed_balance < cost["total"]:
        return _error(
            f"Not enough AI coins. This run costs {cost['total']}, "
            f"you have {claimed_balance}.",
            status=402,   # 402 Payment Required
        )

    # --- Prepare data and train --------------------------------------
    try:
        datasets = prepare_datasets(config["split_ratio"])
    except FileNotFoundError as exc:
        return _error(str(exc), status=500)
    except ValueError as exc:
        return _error(str(exc), status=400)
    except Exception:
        current_app.logger.exception("Dataset preparation failed")
        return _error("Could not prepare the dataset.", status=500)

    try:
        result = train_model(config, datasets)
    except Exception:
        # Do NOT deduct coins on failure, and do not leak a traceback.
        current_app.logger.exception("Training failed")
        return _error(
            "Training failed on the server. No coins were deducted. "
            "Try a smaller configuration or contact the instructor.",
            status=500,
        )

    new_balance = claimed_balance - cost["total"]

    return jsonify({
        "ok": True,
        "result": result,
        "cost": cost,
        "balance": {
            "previous": claimed_balance,
            "spent": cost["total"],
            "remaining": new_balance,
        },
        "config": config,
    })


# ---------------------------------------------------------------------
# /api/reset
# ---------------------------------------------------------------------
@bp.post("/api/reset")
def api_reset():
    payload = request.get_json(silent=True)
    if payload is None:
        return _error("Body must be valid JSON.", status=400)

    code = str(payload.get("code", ""))
    expected = Config.RESET_CODE

    # Constant-time-ish comparison (not cryptographically required here,
    # but avoids the most obvious timing leak).
    import hmac
    if not hmac.compare_digest(code, expected):
        return _error("Invalid reset code.", status=403)

    return jsonify({
        "ok": True,
        "balance": Config.INITIAL_COINS,
        "message": "AI coins reset.",
    })
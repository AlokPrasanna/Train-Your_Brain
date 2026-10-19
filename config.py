import os
from dotenv import load_dotenv


load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

    # Reset code for "Reset AI Coins" — server-side only.
    RESET_CODE = os.getenv("RESET_CODE", "letmein")

    # Coin economy
    INITIAL_COINS = 100
    MISSION_TARGET = 0.75  # validation accuracy >= 75%

    # Allowed parameter values — single source of truth for the whole app.
    ALLOWED_HIDDEN_LAYERS = [1, 2, 3]
    ALLOWED_NEURONS = [4, 8, 16, 32]
    ALLOWED_ACTIVATIONS = ["relu", "tanh", "sigmoid"]
    ALLOWED_EPOCHS = [10, 25, 50, 75, 100]
    ALLOWED_BATCH_SIZES = [8, 16, 32, 64]
    ALLOWED_LEARNING_RATES = [0.01, 0.001, 0.0001]
    ALLOWED_SPLIT_RATIOS = ["60:40", "70:30", "80:20", "90:10"]
    DEFAULT_SPLIT_RATIO = "80:20"

    # Validation fraction carved out of the training portion.
    VALIDATION_FRACTION = 0.2

    # Dataset
    DATASET_PATH = os.path.join("data", "data_banknote_authentication.txt")
    FEATURE_COLUMNS = ["variance", "skewness", "curtosis", "entropy"]
    TARGET_COLUMN = "class"

    # Reproducibility
    RANDOM_SEED = 42

    # Difficulty tuning
    LABEL_NOISE_FRACTION = float(os.getenv("LABEL_NOISE_FRACTION", "0.15"))
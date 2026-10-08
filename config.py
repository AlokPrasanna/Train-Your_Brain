import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    RESET_CODE = os.getenv("RESET_CODE")
    INITIAL_COINS = int(os.getenv("INITIAL_COINS"))
    DATASET_PATH = os.path.join(os.path.dirname(__file__),"data", "data_banknote_authentication.txt")
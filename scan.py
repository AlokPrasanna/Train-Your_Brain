"""Quick accuracy scan across small / mid / large configurations."""
from app.data import prepare_datasets
from app.trainer import train_model

configs = {
    "tiny":   dict(hidden_layers=1, neurons=[4],          activation="relu",
                   epochs=10,  batch_size=64, learning_rate=0.01),
    "small":  dict(hidden_layers=1, neurons=[8],          activation="relu",
                   epochs=25,  batch_size=32, learning_rate=0.001),
    "mid":    dict(hidden_layers=2, neurons=[16, 16],     activation="relu",
                   epochs=50,  batch_size=32, learning_rate=0.001),
    "large":  dict(hidden_layers=3, neurons=[32, 32, 32], activation="relu",
                   epochs=100, batch_size=8,  learning_rate=0.0001),
}

for name, cfg in configs.items():
    cfg["split_ratio"] = "80:20"
    ds = prepare_datasets(cfg["split_ratio"])
    r = train_model(cfg, ds)
    m = r["metrics"]
    print(f"{name:6s}  train={m['train_accuracy']:.4f}  "
          f"val={m['val_accuracy']:.4f}  test={m['test_accuracy']:.4f}")
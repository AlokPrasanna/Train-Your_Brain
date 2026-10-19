# 🧠 Train Your Brain

An interactive Artificial Neural Network (ANN) workshop application for IEEE student sessions. Teams design and train neural networks in the browser, competing to reach **75% validation accuracy** while spending the **fewest AI coins** possible.

Built for **IEEE Day 2026** at the Open University of Sri Lanka.

---

## 📋 Table of Contents

- [What It Does](#-what-it-does)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Local Setup (Virtual Environment)](#-local-setup-virtual-environment)
- [Local Setup (Docker)](#-local-setup-docker)
- [How the Game Works](#-how-the-game-works)
- [API Endpoints](#-api-endpoints)
- [Configuration](#%EF%B8%8F-configuration)
- [Dataset](#-dataset)
- [Running the Experiments Script](#-running-the-experiments-script)
- [Workshop Deployment](#-workshop-deployment)
- [Testing Checklist](#-testing-checklist)
- [License](#-license)
- [Author](#-author)

---

## 🎯 What It Does

Students open a web interface, pick neural network hyperparameters — hidden layers, neurons, activation function, epochs, batch size, learning rate, and data split ratio — and click **"Train Your Brain"**. The backend trains a Keras model on the UCI Banknote Authentication dataset, returns accuracy/loss metrics, and shows charts. Each configuration costs **AI coins** based on its compute footprint, so students must find the most efficient model that hits the accuracy target.

The dataset is deliberately **injected with 25% label noise** so the task is not trivially solvable (the clean Banknote dataset is ~99% accurable by even 4-neuron models). This creates a real underfitting/overfitting tradeoff and makes the 75% target a genuine challenge.

---

## ✨ Features

- **Live configuration** — cost breakdown and generated Keras code update on every parameter change
- **Real training** — TensorFlow/Keras model runs server-side on each request
- **Educational charts** — accuracy and loss curves per epoch, plus a full history table
- **AI coin economy** — 100 starting coins, costs scale with compute, insufficient funds block training
- **Server-side validation** — every parameter is whitelisted on the backend; the client cannot inject arbitrary values
- **Reset mechanism** — instructor-only reset code restores balance to 100
- **Secure by design** — reset code stored in `.env`, never exposed to the browser
- **Docker-ready** — production-style `gunicorn` deployment
- **Bilingual-friendly** — designed for Sinhala/English workshops

---

## 🛠 Tech Stack

| Layer       | Technology                           |
| ----------- | ------------------------------------ |
| Backend     | Python 3.13.5, Flask                 |
| ML          | TensorFlow 2.21.0, Keras             |
| Data        | Pandas, NumPy, scikit-learn          |
| Frontend    | HTML5, CSS3, Bootstrap 5, JavaScript |
| Charts      | Chart.js                             |
| Environment | python-dotenv                        |
| Deployment  | Docker, Gunicorn                     |

---

## 📁 Project Structure

```
train-your-brain/
├── app/
│   ├── __init__.py          # Flask application factory
│   ├── routes.py            # API endpoints and request validation
│   ├── trainer.py           # Model building, training, code generation
│   ├── cost.py              # AI coin pricing rules
│   ├── data.py              # Dataset loading, splitting, scaling
│   ├── templates/
│   │   └── index.html       # Main UI
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── data/
│   └── data_banknote_authentication.txt
├── config.py                # Central configuration
├── run.py                   # Dev entry point
├── experiment.py            # Experimentation script
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── .env.example
├── .gitignore
└── README.md
```

---

## ✅ Prerequisites

- **Git**
- **Docker** (optional, for containerized deployment)
- ~5 GB free disk space for TensorFlow

Check your Python:

```bash
python3 --version
```

---

## 🐍 Local Setup (Virtual Environment)

### 1. Clone the repository

```bash
git clone https://github.com/AlokPrasanna/Train-Your_Brain.git
cd train-your-brain
```

### 2. Create and activate a virtual environment

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate
```

Your prompt should now show `(.venv)`.

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Create `.env`

Copy the template:

```bash
cp .env.example .env
```

Then edit `.env` and set real values:

```bash
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
RESET_CODE=<your-instructor-reset-code>
FLASK_DEBUG=1
LABEL_NOISE_FRACTION=0.25
```

> ⚠️ **Never commit `.env`.** It holds your reset code. Only `.env.example` belongs in Git.

### 5. Download the dataset

```bash
mkdir -p data
wget https://archive.ics.uci.edu/ml/machine-learning-databases/00267/data_banknote_authentication.txt \
     -O data/data_banknote_authentication.txt
```

Verify:

```bash
wc -l data/data_banknote_authentication.txt   # should print 1372
```

### 6. Run the application

```bash
python run.py
```

Open **http://127.0.0.1:5000/**.

---

## 🐳 Local Setup (Docker)

If you have Docker installed, this is the fastest way.

### 1. Build the image

```bash
docker build -t train-your-brain:latest .
```

First build takes 5–10 minutes (TensorFlow download). Rebuilds are fast.

### 2. Run the container

```bash
docker run -d \
  --name tyb \
  -p 5000:5000 \
  --env-file .env \
  train-your-brain:latest
```

### 3. Open

**http://127.0.0.1:5000/**

### 4. Useful commands

```bash
docker logs -f tyb          # follow logs
docker stop tyb             # stop
docker start tyb            # restart
docker exec -it tyb bash    # shell inside
docker rm -f tyb            # delete
```

### Rebuild after code changes

The running container has the _old_ code. Rebuild:

```bash
docker stop tyb && docker rm tyb
docker build -t train-your-brain:latest .
docker run -d --name tyb -p 5000:5000 --env-file .env train-your-brain:latest
```

---

## 🎮 How the Game Works

### Mission

Reach **validation accuracy ≥ 75%** while spending as few **AI coins** as possible.

### Starting budget

Every team starts with **100 AI coins**.

### Pricing

| Parameter         | Options                 | Coins              |
| ----------------- | ----------------------- | ------------------ |
| Base (any run)    | —                       | 5                  |
| Per hidden layer  | 1 / 2 / 3               | 3 each             |
| Neurons per layer | 4 / 8 / 16 / 32         | 2 / 4 / 6 / 10     |
| Activation        | relu / tanh / sigmoid   | 0 / 2 / 3          |
| Epochs            | 10 / 25 / 50 / 75 / 100 | 1 / 3 / 5 / 8 / 10 |
| Batch size        | 8 / 16 / 32 / 64        | 4 / 3 / 1 / 0      |
| Learning rate     | 0.01 / 0.001 / 0.0001   | 0 / 1 / 3          |
| **Data split**    | 80:20 / 70:30 / 60:40   | **Free**           |

**Example costs:**

- Tiny model (1L, 4N, 10 epochs): **11 coins** — 9 runs per team
- Sweet-spot (2L, 16+16, 50 epochs): **30 coins** — 3 runs per team
- Large model (3L, 32×3, 100 epochs): **62 coins** — 1 run per team

### Why 25% label noise?

The clean Banknote dataset is **too easy** — even a 4-neuron model reaches 99%. With 25% of labels randomly flipped, the theoretical accuracy ceiling is **~75%**. This makes the game actually losable and teaches real concepts:

- **Overfitting**: high-capacity models memorize the noise → validation drops
- **Early stopping**: 25 epochs often beats 100
- **Regularization**: small batches (8, 16) help more than large ones (64)
- **Learning rate sensitivity**: 0.01 overfits noise; 0.0001 underfits

**The lesson:** _Bigger is not always better — a smart brain beats a big brain._

---

## 🌐 API Endpoints

| Method | Path           | Purpose                                        |
| ------ | -------------- | ---------------------------------------------- |
| `GET`  | `/`            | Main page                                      |
| `GET`  | `/api/config`  | Allowed values, defaults, mission target       |
| `GET`  | `/api/dataset` | Dataset stats and class distribution           |
| `POST` | `/api/cost`    | Validate config → return cost + generated code |
| `POST` | `/api/train`   | Validate → train → return metrics              |
| `POST` | `/api/reset`   | Validate reset code → confirm reset            |

### Example: `/api/train`

```bash
curl -X POST http://127.0.0.1:5000/api/train \
  -H "Content-Type: application/json" \
  -d '{
    "hidden_layers": 2,
    "neurons": [16, 16],
    "activation": "relu",
    "epochs": 50,
    "batch_size": 32,
    "learning_rate": 0.001,
    "split_ratio": "80:20",
    "balance": 100
  }'
```

**Response (abbreviated):**

```json
{
  "ok": true,
  "result": {
    "metrics": {
      "train_accuracy": 0.8231,
      "val_accuracy": 0.7714,
      "test_accuracy": 0.7635
    },
    "mission": { "achieved": true, "target": 0.75 }
  },
  "cost": { "total": 30 },
  "balance": { "previous": 100, "spent": 30, "remaining": 70 }
}
```

---

## ⚙️ Configuration

All settings live in `config.py` and are overridden by `.env`.

| `.env` variable        | Default                | Purpose                                                  |
| ---------------------- | ---------------------- | -------------------------------------------------------- |
| `SECRET_KEY`           | `dev-secret-change-me` | Flask session signing                                    |
| `RESET_CODE`           | `changeme-reset-code`  | Coin reset authorization                                 |
| `FLASK_DEBUG`          | `1`                    | Verbose errors on/off                                    |
| `LABEL_NOISE_FRACTION` | `0.15`                 | Fraction of labels flipped (0 = off, 0.25 = recommended) |

Change the allowed parameter values (epochs, batch sizes, etc.) by editing `Config.ALLOWED_*` in `config.py`. They propagate to the UI automatically via `/api/config`.

---

## 📊 Dataset

**UCI Banknote Authentication** — 1,372 rows, 4 numeric features, binary classification.

| Feature  | Description                        |
| -------- | ---------------------------------- |
| Variance | Wavelet-transformed image variance |
| Skewness | Wavelet-transformed image skewness |
| Curtosis | Wavelet-transformed image curtosis |
| Entropy  | Image entropy                      |

**Class distribution:** 762 authentic (55%) / 610 inauthentic (45%)

**Preprocessing:**

1. Stratified split according to the chosen ratio (80:20 / 70:30 / 60:40)
2. 20% of the train+val portion is held out for **validation**
3. `StandardScaler` fitted on **training data only** — no leakage
4. Label noise injected deterministically (seeded) before splitting

Download from the official source: [https://archive.ics.uci.edu/dataset/267/banknote+authentication](https://archive.ics.uci.edu/dataset/267/banknote+authentication)

---

## 🔬 Running the Experiments Script

To calibrate difficulty before a workshop:

```bash
python experiment.py
```

This runs a grid of predefined configurations with the same preprocessing as the app, and writes `experiment_results.csv` with validation accuracy, test accuracy, duration, and cost. Use it to confirm that:

- Small models score 65–75%
- Mid models score 72–77%
- Large models overfit (train high, validation lower)

Adjust `LABEL_NOISE_FRACTION` until the spread looks right.

---

## 🚀 Workshop Deployment

**Do NOT use Flask's development server for 10+ teams.** It handles one request at a time.

### Recommended setup

1. **Use Docker with Gunicorn** (already configured in the Dockerfile)
2. **Bind to `0.0.0.0`** so other machines on the LAN can reach it
3. **Run on a laptop with at least 8 GB RAM** (TensorFlow + concurrent requests)
4. **Add `-p 0.0.0.0:5000:5000`** if using Docker on a shared network

### Accessing from student laptops

Find the host machine's LAN IP:

```bash
hostname -I
# e.g. 192.168.1.42
```

Students open: `http://192.168.1.42:5000/`

### Pre-flight checklist

- [ ] `.env` exists with a **real** reset code
- [ ] `LABEL_NOISE_FRACTION` set to the calibrated value
- [ ] Dataset file verified (`wc -l` = 1372)
- [ ] One test training run completed
- [ ] Reset code tested (correct + incorrect)
- [ ] Browser tested on at least one student device
- [ ] Backup screenshots prepared in case of network issues

---

## 🧪 Testing Checklist

- [ ] Initial balance is 100
- [ ] All parameter dropdowns populate from `/api/config`
- [ ] Changing layer count rebuilds neuron selectors
- [ ] Cost breakdown updates on every parameter change
- [ ] Generated code matches the config
- [ ] Insufficient coins block the Train button
- [ ] Training success deducts coins correctly
- [ ] Failed training does **not** deduct coins
- [ ] Mission banner shows success at ≥75% val accuracy
- [ ] Charts and history table render
- [ ] Correct reset code restores balance to 100
- [ ] Wrong reset code is rejected
- [ ] `.env` is NOT in the Docker image (`docker run --rm train-your-brain:latest ls /app/.env`)
- [ ] `Config.RESET_CODE` inside container equals your `.env` value

---

## 📄 License

MIT License — free to use, modify, and share for educational purposes.

---

## 👤 Author

**Alok Prasanna Jayathilaka**  
Data Science MSc Student — Open University of Sri Lanka  
Built for **IEEE Day 2026** 🚀

---

_"Can you build a smart brain — not just a big one?"_

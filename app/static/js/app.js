/* =====================================================================
   Train Your Brain — frontend logic (Part A)

   Responsibilities in this file:
     - Load /api/config and /api/dataset on page load.
     - Manage the live configuration state (single source of truth).
     - Rebuild neuron selectors when the hidden-layer count changes.
     - On any parameter change, POST to /api/cost (debounced) and update
       the cost receipt and the generated-code panel.
     - Manage the coin balance in LocalStorage (v1 prototype only —
       the README will spell out why this is not secure).

   Part B (appended later) adds the training flow, charts, and reset modal.
   ===================================================================== */

"use strict";

/* ---------------------------------------------------------------------
   1. Constants
   --------------------------------------------------------------------- */

const STORAGE_KEY_BALANCE = "tyb.balance";
const STORAGE_KEY_CONFIG = "tyb.config"; // remembers last selection
const COST_DEBOUNCE_MS = 250; // wait after a change before POST

/* DOM shortcuts (by id). Populated once at startup. */
const el = {};

/* Live configuration state. Kept in sync with the UI. */
const state = {
  allowed: null, // filled from /api/config
  initialCoins: 100, // overwritten from /api/config
  missionTarget: 0.75, // overwritten from /api/config
  validationFraction: 0.2,
  balance: 0, // managed via LocalStorage
  config: {
    // current selection
    hidden_layers: 2,
    neurons: [16, 16],
    activation: "relu",
    epochs: 50,
    batch_size: 32,
    learning_rate: 0.001,
    split_ratio: "80:20",
  },
  training: false, // true while a /api/train request is in flight
  cost: null, // last successful cost response
};

let costDebounceTimer = null;

/* ---------------------------------------------------------------------
   2. Small helpers
   --------------------------------------------------------------------- */

/** Shorthand for document.getElementById. */
function $(id) {
  return document.getElementById(id);
}

/** Format a number with up to `digits` decimals, dropping trailing zeros. */
function fmt(num, digits = 4) {
  if (num === null || num === undefined || Number.isNaN(num)) return "—";
  return (
    Number(num)
      .toFixed(digits)
      .replace(/\.?0+$/, "") || "0"
  );
}

/** Format a decimal as a percentage string, e.g. 0.9412 -> "94.12%". */
function pct(num, digits = 2) {
  if (num === null || num === undefined || Number.isNaN(num)) return "—";
  return (num * 100).toFixed(digits) + "%";
}

/** Show a message in the shared error modal. */
function showError(message) {
  $("error-message").textContent = message;
  const modal = bootstrap.Modal.getOrCreateInstance($("errorModal"));
  modal.show();
}

/** Set the header status badge. `kind` is one of: idle, training, success, error. */
function setStatus(kind, label) {
  const badge = el.statusBadge;
  badge.classList.remove("is-training", "is-success", "is-error");
  if (kind === "training") badge.classList.add("is-training");
  if (kind === "success") badge.classList.add("is-success");
  if (kind === "error") badge.classList.add("is-error");

  const icons = {
    idle: "bi-circle",
    training: "bi-hourglass-split",
    success: "bi-check-circle",
    error: "bi-x-circle",
  };
  badge.innerHTML = `<i class="bi ${icons[kind] || icons.idle}"></i> ${label}`;
}

/* ---------------------------------------------------------------------
   3. LocalStorage balance (v1 prototype only)
   --------------------------------------------------------------------- */

function loadBalance() {
  const raw = localStorage.getItem(STORAGE_KEY_BALANCE);
  const parsed = raw === null ? null : Number(raw);
  if (parsed === null || Number.isNaN(parsed) || parsed < 0) {
    return state.initialCoins;
  }
  return parsed;
}

function saveBalance(value) {
  state.balance = value;
  localStorage.setItem(STORAGE_KEY_BALANCE, String(value));
  el.coinBalance.textContent = String(value);
}

/* ---------------------------------------------------------------------
   4. Bootstrap wiring — cache DOM refs
   --------------------------------------------------------------------- */

function cacheDom() {
  el.coinBalance = $("coin-balance");
  el.statusBadge = $("status-badge");

  el.hiddenLayers = $("hidden-layers");
  el.neuronsContainer = $("neurons-container");
  el.activation = $("activation");
  el.epochs = $("epochs");
  el.batchSize = $("batch-size");
  el.learningRate = $("learning-rate");
  el.splitRatio = $("split-ratio");

  el.costTotal = $("cost-total");
  el.costBreakdown = $("cost-breakdown");
  el.generatedCode = $("generated-code");
  el.splitSummary = $("split-summary");

  el.trainBtn = $("train-btn");
  el.resetBtn = $("reset-btn");

  el.resultsCard = $("results-card");
  el.resultsBody = $("results-body");
  el.missionBanner = $("mission-banner");
  el.historyBody = $("history-body");

  el.datasetInfo = $("dataset-info");
  el.datasetPath = $("dataset-path");

  el.resetCodeInput = $("reset-code-input");
  el.resetError = $("reset-error");
  el.resetConfirmBtn = $("reset-confirm-btn");
}

/* ---------------------------------------------------------------------
   5. /api/config — load allowed values and defaults
   --------------------------------------------------------------------- */

async function loadConfig() {
  const res = await fetch("/api/config");
  const data = await res.json();
  if (!data.ok) throw new Error(data.error || "Failed to load configuration.");

  state.allowed = data.allowed;
  state.initialCoins = data.initial_coins;
  state.missionTarget = data.mission_target;
  state.validationFraction = data.validation_fraction;

  // Populate dropdown options from the server (single source of truth).
  fillSelect(
    el.hiddenLayers,
    data.allowed.hidden_layers,
    (v) => `${v} hidden layer${v > 1 ? "s" : ""}`,
  );
  fillSelect(
    el.activation,
    data.allowed.activations,
    (v) => v.charAt(0).toUpperCase() + v.slice(1),
  );
  fillSelect(el.epochs, data.allowed.epochs, (v) => String(v));
  fillSelect(el.batchSize, data.allowed.batch_sizes, (v) => String(v));
  fillSelect(el.learningRate, data.allowed.learning_rates, (v) => String(v));
  fillSelect(el.splitRatio, data.allowed.split_ratios, (v) =>
    v.replace(":", " : "),
  );

  // Apply stored / default selection.
  const stored = readStoredConfig();
  const defaults = stored || data.defaults;
  applyConfigToUI(defaults);

  // Balance.
  state.balance = loadBalance();
  el.coinBalance.textContent = String(state.balance);
}

/** Populate a <select> with a list of values. */
function fillSelect(select, values, labelFn) {
  select.innerHTML = "";
  for (const v of values) {
    const opt = document.createElement("option");
    opt.value = String(v);
    opt.textContent = labelFn ? labelFn(v) : String(v);
    select.appendChild(opt);
  }
}

/** Persist the current config to LocalStorage so a reload feels continuous. */
function storeConfig() {
  localStorage.setItem(STORAGE_KEY_CONFIG, JSON.stringify(state.config));
}

function readStoredConfig() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_CONFIG);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    // Minimal sanity: the shape must contain all the keys we need.
    const keys = [
      "hidden_layers",
      "neurons",
      "activation",
      "epochs",
      "batch_size",
      "learning_rate",
      "split_ratio",
    ];
    for (const k of keys) if (!(k in parsed)) return null;
    return parsed;
  } catch {
    return null;
  }
}

/** Push a config object into the DOM controls. */
function applyConfigToUI(cfg) {
  el.hiddenLayers.value = String(cfg.hidden_layers);
  el.activation.value = cfg.activation;
  el.epochs.value = String(cfg.epochs);
  el.batchSize.value = String(cfg.batch_size);
  el.learningRate.value = String(cfg.learning_rate);
  el.splitRatio.value = cfg.split_ratio;

  renderNeuronSelectors(cfg.hidden_layers, cfg.neurons);
  syncStateFromUI();
}

/* ---------------------------------------------------------------------
   6. Neuron selectors — rebuild when layer count changes
   --------------------------------------------------------------------- */

function renderNeuronSelectors(layerCount, currentNeurons) {
  const container = el.neuronsContainer;
  container.innerHTML = "";

  const allowedNeurons = state.allowed.neurons;

  for (let i = 0; i < layerCount; i++) {
    const col = document.createElement("div");
    col.className = "col-6 col-md-3";

    const label = document.createElement("label");
    label.className = "form-label small mb-1";
    label.textContent = `Layer ${i + 1}`;

    const select = document.createElement("select");
    select.className = "form-select form-select-sm";
    select.dataset.layerIndex = String(i);
    select.id = `neurons-layer-${i}`;

    for (const n of allowedNeurons) {
      const opt = document.createElement("option");
      opt.value = String(n);
      opt.textContent = `${n}`;
      select.appendChild(opt);
    }

    const want = (currentNeurons && currentNeurons[i]) || allowedNeurons[0];
    select.value = String(want);

    select.addEventListener("change", onAnyParamChange);

    col.appendChild(label);
    col.appendChild(select);
    container.appendChild(col);
  }
}

/** Read the current neuron counts from the rendered selects. */
function readNeuronsFromUI() {
  return Array.from(el.neuronsContainer.querySelectorAll("select")).map((s) =>
    parseInt(s.value, 10),
  );
}

/* ---------------------------------------------------------------------
   7. State sync + change handling
   --------------------------------------------------------------------- */

/** Pull every control's value into `state.config`. */
function syncStateFromUI() {
  state.config.hidden_layers = parseInt(el.hiddenLayers.value, 10);
  state.config.neurons = readNeuronsFromUI();
  state.config.activation = el.activation.value;
  state.config.epochs = parseInt(el.epochs.value, 10);
  state.config.batch_size = parseInt(el.batchSize.value, 10);
  state.config.learning_rate = parseFloat(el.learningRate.value);
  state.config.split_ratio = el.splitRatio.value;
}

/** Called by any input's change event. */
function onAnyParamChange() {
  const previousLayers = state.config.hidden_layers;
  const previousNeurons = state.config.neurons;

  const newLayers = parseInt(el.hiddenLayers.value, 10);

  if (newLayers !== previousLayers) {
    // Preserve the neurons already chosen for existing layers.
    const carry = previousNeurons.slice(0, newLayers);
    while (carry.length < newLayers) carry.push(16); // sensible default
    renderNeuronSelectors(newLayers, carry);
  }

  syncStateFromUI();
  storeConfig();

  // Refresh cost + code (debounced).
  if (costDebounceTimer) clearTimeout(costDebounceTimer);
  costDebounceTimer = setTimeout(refreshCostAndCode, COST_DEBOUNCE_MS);
}

/* ---------------------------------------------------------------------
   8. /api/cost — update receipt and code panel
   --------------------------------------------------------------------- */

async function refreshCostAndCode() {
  try {
    const res = await fetch("/api/cost", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.config),
    });
    const data = await res.json();

    if (!data.ok) {
      el.costTotal.textContent = "—";
      el.costBreakdown.innerHTML = `<li class="list-group-item text-danger small">${escapeHtml(data.error || "Invalid configuration.")}</li>`;
      el.generatedCode.textContent =
        "# Fix the configuration to see generated code.";
      updateTrainButtonState();
      return;
    }

    state.cost = data.cost;
    renderCostBreakdown(data.cost);
    renderGeneratedCode(data.code);
    updateSplitSummary();
    updateTrainButtonState();
  } catch (err) {
    console.error("Cost refresh failed:", err);
    el.costTotal.textContent = "—";
    el.costBreakdown.innerHTML = `<li class="list-group-item text-danger small">Could not reach the server.</li>`;
  }
}

function renderCostBreakdown(cost) {
  el.costTotal.textContent = String(cost.total);

  const rows = cost.breakdown.map((item) => {
    const coins =
      item.coins === 0
        ? `<span class="text-muted">free</span>`
        : `<span class="cost-coins">${item.coins}</span>`;
    return `
      <li class="list-group-item d-flex justify-content-between align-items-start gap-2">
        <div class="flex-grow-1">
          <div class="cost-label">${escapeHtml(item.label)}</div>
          <div class="cost-detail">${escapeHtml(item.detail || "")}</div>
        </div>
        <div class="text-nowrap">${coins}</div>
      </li>`;
  });

  el.costBreakdown.innerHTML = rows.join("");
}

function renderGeneratedCode(code) {
  // Use textContent — not innerHTML — to avoid executing anything.
  el.generatedCode.textContent = code;
}

/** Show students what the split ratio actually does to the row counts. */
function updateSplitSummary() {
  const [train, test] = state.config.split_ratio
    .split(":")
    .map((n) => parseInt(n, 10));
  const totalRows = 1372; // matches the dataset
  const trainvalRows = Math.round(totalRows * (train / 100));
  const testRows = totalRows - trainvalRows;
  const valRows = Math.round(trainvalRows * state.validationFraction);
  const actualTrain = trainvalRows - valRows;

  el.splitSummary.innerHTML = `
    <i class="bi bi-info-circle"></i>
    <strong>${state.config.split_ratio}</strong> split
    &rarr; <strong>${actualTrain}</strong> train
    / <strong>${valRows}</strong> validation
    / <strong>${testRows}</strong> test rows.
    Validation is ${Math.round(state.validationFraction * 100)}% of the train+val portion.
  `;
}

/** Enable/disable the train button based on cost vs balance. */
function updateTrainButtonState() {
  if (state.training) {
    el.trainBtn.disabled = true;
    return;
  }
  if (!state.cost) {
    el.trainBtn.disabled = false;
    return;
  }
  const canAfford = state.balance >= state.cost.total;
  el.trainBtn.disabled = !canAfford;
  el.trainBtn.innerHTML = canAfford
    ? `<i class="bi bi-rocket-takeoff"></i> Train Your Brain (${state.cost.total} coins)`
    : `<i class="bi bi-slash-circle"></i> Not enough coins (${state.cost.total} needed)`;
}

/* ---------------------------------------------------------------------
   9. Utility
   --------------------------------------------------------------------- */

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/* ---------------------------------------------------------------------
   10. Dataset info card
   --------------------------------------------------------------------- */

async function loadDatasetInfo() {
  try {
    const res = await fetch("/api/dataset");
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "Failed to load dataset.");

    const d = data.dataset;
    el.datasetPath.textContent = d.path;
    const noisePct = Math.round((d.label_noise_fraction || 0) * 100);
    const ceilingPct = Math.round((d.accuracy_ceiling_estimate || 1) * 100);
    el.datasetInfo.innerHTML = `
      <div class="col-sm-4"><div class="text-muted small">Rows</div>
        <div class="fw-semibold">${d.rows}</div></div>
      <div class="col-sm-4"><div class="text-muted small">Features</div>
        <div class="fw-semibold">${d.features.length}</div></div>
      <div class="col-sm-4"><div class="text-muted small">Classes</div>
        <div class="fw-semibold">
          ${d.class_distribution.class_0} / ${d.class_distribution.class_1}
        </div></div>
      <div class="col-12"><div class="text-muted small">Feature names</div>
        <div class="fw-semibold">${d.features.join(", ")}</div></div>
    `;
  } catch (err) {
    el.datasetInfo.innerHTML = `<div class="col-12 text-danger small">Could not load dataset: ${escapeHtml(err.message)}</div>`;
  }
}

/* ---------------------------------------------------------------------
   11. Event wiring (Part A)
   --------------------------------------------------------------------- */

function wireEvents() {
  // Any change to a parameter triggers a debounced cost refresh.
  [
    el.hiddenLayers,
    el.activation,
    el.epochs,
    el.batchSize,
    el.learningRate,
    el.splitRatio,
  ].forEach((ctrl) => ctrl.addEventListener("change", onAnyParamChange));
}

/* ---------------------------------------------------------------------
   12. Init (Part A)
   --------------------------------------------------------------------- */

async function init() {
  cacheDom();

  try {
    await loadConfig();
  } catch (err) {
    showError("Could not load application configuration: " + err.message);
    return;
  }

  wireEvents();

  // Wire Part B interactions.
  el.trainBtn.addEventListener("click", train);
  el.resetConfirmBtn.addEventListener("click", resetCoins);
  el.resetCodeInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      resetCoins();
    }
  });
  // Clear reset error each time the modal opens.
  $("resetModal").addEventListener("show.bs.modal", () => {
    el.resetError.classList.add("d-none");
    el.resetError.textContent = "";
    el.resetCodeInput.value = "";
    el.resetCodeInput.focus();
  });

  // Charts must be created before the results card is shown.
  initCharts();

  await Promise.all([loadDatasetInfo(), refreshCostAndCode()]);
  setStatus("idle", "Idle");

  console.log("[Train Your Brain] Ready.");
}

document.addEventListener("DOMContentLoaded", init);

document.addEventListener("DOMContentLoaded", init);

/* ---------------------------------------------------------------------
   13. Charts — created once, updated on every training run
   --------------------------------------------------------------------- */

let accuracyChart = null;
let lossChart = null;

function initCharts() {
  const commonOptions = (yLabel) => ({
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { position: "bottom" },
      tooltip: {
        callbacks: {
          label: (ctx) => `${ctx.dataset.label}: ${fmt(ctx.parsed.y, 4)}`,
        },
      },
    },
    scales: {
      x: { title: { display: true, text: "Epoch" } },
      y: { title: { display: true, text: yLabel }, beginAtZero: true },
    },
  });

  accuracyChart = new Chart($("chart-accuracy"), {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Train",
          data: [],
          borderColor: "#3b5bdb",
          backgroundColor: "rgba(59,91,219,0.10)",
          tension: 0.25,
        },
        {
          label: "Validation",
          data: [],
          borderColor: "#f59f00",
          backgroundColor: "rgba(245,159,0,0.10)",
          tension: 0.25,
        },
      ],
    },
    options: commonOptions("Accuracy"),
  });

  lossChart = new Chart($("chart-loss"), {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Train",
          data: [],
          borderColor: "#3b5bdb",
          backgroundColor: "rgba(59,91,219,0.10)",
          tension: 0.25,
        },
        {
          label: "Validation",
          data: [],
          borderColor: "#e03131",
          backgroundColor: "rgba(224,49,49,0.10)",
          tension: 0.25,
        },
      ],
    },
    options: commonOptions("Loss"),
  });
}

function updateCharts(history) {
  const epochs = history.accuracy.map((_, i) => i + 1);

  accuracyChart.data.labels = epochs;
  accuracyChart.data.datasets[0].data = history.accuracy;
  accuracyChart.data.datasets[1].data = history.val_accuracy;
  accuracyChart.update();

  lossChart.data.labels = epochs;
  lossChart.data.datasets[0].data = history.loss;
  lossChart.data.datasets[1].data = history.val_loss;
  lossChart.update();
}

/* ---------------------------------------------------------------------
   14. Results rendering
   --------------------------------------------------------------------- */

function renderResults(payload) {
  const { result, cost, balance } = payload;
  const m = result.metrics;

  // --- Metric rows ---
  const rows = [
    ["Final training accuracy", pct(m.train_accuracy)],
    ["Final validation accuracy", pct(m.val_accuracy)],
    ["Test accuracy", pct(m.test_accuracy)],
    ["Test loss", fmt(m.test_loss, 4)],
    ["Training duration", `${fmt(result.duration_seconds, 2)} s`],
    ["Coins spent on this run", `${cost.total}`],
    ["Remaining coins", `${balance.remaining}`],
    ["Split ratio used", result.split_summary.split_ratio],
  ];

  el.resultsBody.innerHTML = rows
    .map(
      ([k, v]) => `<tr><td>${escapeHtml(k)}</td><td>${escapeHtml(v)}</td></tr>`,
    )
    .join("");

  // --- Mission banner ---
  const achieved = result.mission.achieved;
  el.missionBanner.className =
    "alert " + (achieved ? "alert-success" : "alert-warning");
  el.missionBanner.innerHTML = achieved
    ? `<i class="bi bi-trophy-fill"></i> <strong>Mission accomplished!</strong>
       Validation accuracy ${pct(m.val_accuracy)} ≥ target ${pct(result.mission.target)}.`
    : `<i class="bi bi-arrow-repeat"></i> <strong>Keep experimenting.</strong>
       Validation accuracy ${pct(m.val_accuracy)} is below the target ${pct(result.mission.target)}.
       Try a different architecture or more epochs — but watch your coins.`;

  // --- History table ---
  const rows2 = [];
  const h = result.history;
  for (let i = 0; i < h.accuracy.length; i++) {
    rows2.push(`
      <tr>
        <td>${i + 1}</td>
        <td>${pct(h.accuracy[i], 3)}</td>
        <td>${pct(h.val_accuracy[i], 3)}</td>
        <td>${fmt(h.loss[i], 4)}</td>
        <td>${fmt(h.val_loss[i], 4)}</td>
      </tr>`);
  }
  el.historyBody.innerHTML = rows2.join("");

  // --- Charts ---
  updateCharts(result.history);

  // --- Reveal results card ---
  el.resultsCard.classList.remove("d-none");
}

/* ---------------------------------------------------------------------
   15. Training flow
   --------------------------------------------------------------------- */

async function train() {
  if (state.training) return; // guard against double-clicks

  state.training = true;
  setStatus("training", "Training…");
  el.trainBtn.disabled = true;
  el.trainBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span> Training your brain…`;

  try {
    const res = await fetch("/api/train", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...state.config, balance: state.balance }),
    });
    const data = await res.json();

    if (!data.ok) {
      // Training failed — do NOT deduct coins.
      setStatus("error", "Training failed");
      showError(data.error || "Training failed. No coins were deducted.");
      return;
    }

    // Success: update balance from server response, render everything.
    saveBalance(data.balance.remaining);
    renderResults(data);
    setStatus("success", "Done");
  } catch (err) {
    setStatus("error", "Network error");
    showError("Could not reach the server: " + err.message);
  } finally {
    state.training = false;
    // Recompute button state and label from the (possibly updated) balance.
    updateTrainButtonState();
  }
}

/* ---------------------------------------------------------------------
   16. Reset coins
   --------------------------------------------------------------------- */

async function resetCoins() {
  const code = el.resetCodeInput.value.trim();
  el.resetError.classList.add("d-none");
  el.resetError.textContent = "";

  if (!code) {
    el.resetError.textContent = "Please enter the reset code.";
    el.resetError.classList.remove("d-none");
    return;
  }

  el.resetConfirmBtn.disabled = true;
  el.resetConfirmBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> Resetting…`;

  try {
    const res = await fetch("/api/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    const data = await res.json();

    if (!data.ok) {
      el.resetError.textContent = data.error || "Reset failed.";
      el.resetError.classList.remove("d-none");
      return;
    }

    saveBalance(data.balance);
    updateTrainButtonState();

    // Close the modal and clear the input.
    const modal = bootstrap.Modal.getInstance($("resetModal"));
    if (modal) modal.hide();
    el.resetCodeInput.value = "";
    setStatus("idle", "Idle");
  } catch (err) {
    el.resetError.textContent = "Network error: " + err.message;
    el.resetError.classList.remove("d-none");
  } finally {
    el.resetConfirmBtn.disabled = false;
    el.resetConfirmBtn.textContent = "Reset";
  }
}

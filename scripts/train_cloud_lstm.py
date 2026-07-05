#!/usr/bin/env python3
"""Train and evaluate the cloud-tier LSTM autoencoder verifier (Phase 3).

The hybrid direction stages a light unsupervised filter at the edge (Isolation
Forest, Phase 1) and a heavier model in the cloud that re-examines only the
readings the edge escalated (Phase 2 gate). This script trains that cloud
model: an LSTM autoencoder that learns to reconstruct *normal* telemetry
dynamics. At inference a reading whose reconstruction error exceeds a
threshold (a quantile of normal reconstruction errors) is *confirmed*
anomalous; readings the edge flagged but the cloud reconstructs well are
treated as edge false positives and can be suppressed.

Training uses the same simulator-mirroring data generators as the edge model
(``scripts/train_anomaly_model.py``) so the two tiers see a consistent world.
Features are the physics-informed vector shared with the gateway detector
(``physics_v1``): [v, i, p, t, |v-Vnom|, p - v*i].

The trained weights are exported to a numpy ``.npz`` artifact so the cloud
service can run inference with numpy alone (no torch in the container). This
script also runs the identical forward pass in numpy and asserts parity with
torch before exporting, guaranteeing the shipped kernel matches training.

Usage:
    uv run --group ml-train python scripts/train_cloud_lstm.py            # train + export
    uv run --group ml-train python scripts/train_cloud_lstm.py --evaluate # + two-stage eval
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

# Reuse the exact data-generation + feature transform used by the edge model.
from train_anomaly_model import (  # type: ignore[import-not-found]
    ENGINEERING,
    FEATURES,
    NOMINAL_VOLTAGE,
    engineer,
    generate_anomalies,
    generate_normal,
    score_raw,
)

WINDOW = 8  # readings per escalation window the cloud reconstructs


def make_windows(x: np.ndarray, window: int, rng: np.random.Generator) -> np.ndarray:
    """Assemble ``(N, window, F)`` sequences by sampling rows.

    The simulator emits per-tick readings that are conditionally independent
    given the usage band, so a window is a short run of readings from the same
    world rather than an autoregressive series. The autoencoder therefore
    learns the normal *joint distribution* of a window; this matches how the
    live gateway batches escalated readings before forwarding.
    """
    f = engineer(x)
    n_windows = len(f) // window
    trimmed = f[: n_windows * window]
    seqs = trimmed.reshape(n_windows, window, f.shape[1])
    perm = rng.permutation(n_windows)
    return seqs[perm]


# --------------------------------------------------------------------------
# numpy inference kernel (shipped to the cloud service; parity-checked below)
# --------------------------------------------------------------------------
def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def lstm_forward(
    seq: np.ndarray,
    w_ih: np.ndarray,
    w_hh: np.ndarray,
    b_ih: np.ndarray,
    b_hh: np.ndarray,
    hidden: int,
) -> np.ndarray:
    """Single-layer LSTM forward over ``seq`` (T, input). Returns all hidden
    states (T, hidden). PyTorch gate order: input, forget, cell, output."""
    t_steps = seq.shape[0]
    h = np.zeros(hidden)
    c = np.zeros(hidden)
    outs = np.empty((t_steps, hidden))
    for t in range(t_steps):
        g = w_ih @ seq[t] + b_ih + w_hh @ h + b_hh
        i = _sigmoid(g[:hidden])
        f = _sigmoid(g[hidden : 2 * hidden])
        gg = np.tanh(g[2 * hidden : 3 * hidden])
        o = _sigmoid(g[3 * hidden :])
        c = f * c + i * gg
        h = o * np.tanh(c)
        outs[t] = h
    return outs


def reconstruct_np(seq: np.ndarray, p: dict[str, np.ndarray]) -> np.ndarray:
    """Reconstruct a standardized window ``(T, F)`` with the numpy kernel."""
    hidden = int(p["hidden"])
    enc = lstm_forward(seq, p["enc_w_ih"], p["enc_w_hh"], p["enc_b_ih"], p["enc_b_hh"], hidden)
    latent = enc[-1]
    dec_in = np.tile(latent, (seq.shape[0], 1))
    dec = lstm_forward(dec_in, p["dec_w_ih"], p["dec_w_hh"], p["dec_b_ih"], p["dec_b_hh"], hidden)
    return dec @ p["out_w"].T + p["out_b"]


def recon_error_np(seq: np.ndarray, p: dict[str, np.ndarray]) -> np.ndarray:
    """Per-timestep reconstruction MSE for a standardized window."""
    recon = reconstruct_np(seq, p)
    return np.mean((recon - seq) ** 2, axis=1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="models/cloud_lstm_ae.npz")
    parser.add_argument("--report-dir", default="results/cloud_model")
    parser.add_argument("--version", default="lstm_ae_v1")
    parser.add_argument("--train-windows", type=int, default=6000)
    parser.add_argument("--hidden", type=int, default=16)
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-2)
    parser.add_argument("--threshold-quantile", type=float, default=0.95)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--evaluate", action="store_true")
    args = parser.parse_args()

    import torch
    from torch import nn

    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)

    n_rows = args.train_windows * WINDOW
    print(f"Generating {n_rows} normal readings -> {args.train_windows} windows...")
    x_train = generate_normal(n_rows, rng)
    windows = make_windows(x_train, WINDOW, rng)

    # Standardize features on the training windows (per-feature).
    flat = windows.reshape(-1, windows.shape[2])
    mean = flat.mean(axis=0)
    std = flat.std(axis=0) + 1e-8
    z = (windows - mean) / std
    data = torch.tensor(z, dtype=torch.float32)

    input_size = windows.shape[2]
    hidden = args.hidden

    class LSTMAE(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.enc = nn.LSTM(input_size, hidden, batch_first=True)
            self.dec = nn.LSTM(hidden, hidden, batch_first=True)
            self.out = nn.Linear(hidden, input_size)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            _, (h, _) = self.enc(x)
            latent = h[-1].unsqueeze(1).repeat(1, x.shape[1], 1)
            dec, _ = self.dec(latent)
            return self.out(dec)

    model = LSTMAE()
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.MSELoss()

    print(f"Training LSTM-AE (hidden={hidden}, epochs={args.epochs})...")
    n = data.shape[0]
    for epoch in range(args.epochs):
        model.train()
        perm = torch.randperm(n)
        total = 0.0
        for i in range(0, n, args.batch_size):
            batch = data[perm[i : i + args.batch_size]]
            opt.zero_grad()
            recon = model(batch)
            loss = loss_fn(recon, batch)
            loss.backward()
            opt.step()
            total += loss.item() * batch.shape[0]
        print(f"  epoch {epoch + 1:2d}/{args.epochs}  mse={total / n:.6f}")

    model.eval()

    # Export weights to a numpy-friendly dict.
    sd = model.state_dict()
    params: dict[str, np.ndarray] = {
        "enc_w_ih": sd["enc.weight_ih_l0"].numpy(),
        "enc_w_hh": sd["enc.weight_hh_l0"].numpy(),
        "enc_b_ih": sd["enc.bias_ih_l0"].numpy(),
        "enc_b_hh": sd["enc.bias_hh_l0"].numpy(),
        "dec_w_ih": sd["dec.weight_ih_l0"].numpy(),
        "dec_w_hh": sd["dec.weight_hh_l0"].numpy(),
        "dec_b_ih": sd["dec.bias_ih_l0"].numpy(),
        "dec_b_hh": sd["dec.bias_hh_l0"].numpy(),
        "out_w": sd["out.weight"].numpy(),
        "out_b": sd["out.bias"].numpy(),
        "mean": mean,
        "std": std,
        "hidden": np.array(hidden),
    }

    # Parity check: numpy kernel must match torch on a sample window.
    with torch.no_grad():
        sample = data[:4]
        torch_recon = model(sample).numpy()
    np_recon = np.stack([reconstruct_np(sample[k].numpy(), params) for k in range(4)])
    max_err = float(np.abs(torch_recon - np_recon).max())
    print(f"numpy/torch parity max abs error: {max_err:.2e}")
    assert max_err < 1e-4, f"numpy kernel diverges from torch ({max_err})"

    # Threshold from per-timestep reconstruction error on normal windows.
    with torch.no_grad():
        recon_all = model(data).numpy()
    err_normal = np.mean((recon_all - z) ** 2, axis=2).reshape(-1)
    threshold = float(np.quantile(err_normal, args.threshold_quantile))
    print(f"Reconstruction-error threshold (q={args.threshold_quantile}): {threshold:.6f}")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "version": args.version,
        "features": FEATURES,
        "engineering": ENGINEERING,
        "nominal_voltage": NOMINAL_VOLTAGE,
        "window": WINDOW,
        "hidden": hidden,
        "threshold": threshold,
        "threshold_quantile": args.threshold_quantile,
        "trained_at": datetime.now(UTC).isoformat(),
        "epochs": args.epochs,
        "seed": args.seed,
    }
    np.savez(out, meta=json.dumps(meta), threshold=np.array(threshold), **params)
    print(f"Saved cloud model artifact -> {out}")

    if not args.evaluate:
        return 0

    _evaluate(params, threshold, mean, std, rng, args)
    return 0


def _score_windows_np(x_rows: np.ndarray, params: dict, mean, std) -> np.ndarray:
    """Per-reading reconstruction error for raw [v,i,p,t] rows via the numpy
    kernel, windowed by WINDOW (drops the trailing partial window)."""
    f = engineer(x_rows)
    n_win = len(f) // WINDOW
    f = f[: n_win * WINDOW].reshape(n_win, WINDOW, f.shape[1])
    z = (f - mean) / std
    errs = np.concatenate([recon_error_np(z[k], params) for k in range(n_win)])
    return errs  # aligned to the first n_win*WINDOW rows


def _evaluate(params, threshold, mean, std, rng, args) -> None:
    """Two-stage evaluation: edge IF gate -> cloud verifier, vs edge alone.

    The cloud only ever sees readings the edge escalated, so cloud recall is
    conditional on the edge having flagged the reading. We report the edge's
    own precision/recall and the end-to-end two-stage numbers on the same
    labeled set, so the effect of the cloud confirmation step is visible.
    """
    import joblib

    edge_path = Path("models/anomaly_iforest.joblib")
    if not edge_path.exists():
        print("Edge model artifact missing; run train_anomaly_model.py first.")
        return
    bundle = joblib.load(edge_path)
    ed_model, ed_scaler, ed_thr = bundle["model"], bundle["scaler"], bundle["threshold"]

    n_norm, n_anom = 8000, 2000
    x_norm = generate_normal(n_norm, rng)
    x_anom, labels = generate_anomalies(n_anom, rng)
    labels = np.array(labels)

    # Edge scores (per reading).
    edge_norm = score_raw(ed_model, ed_scaler, x_norm) > ed_thr
    edge_anom = score_raw(ed_model, ed_scaler, x_anom) > ed_thr

    # Cloud reconstruction errors (windowed; align labels to windowed length).
    cloud_norm_err = _score_windows_np(x_norm, params, mean, std)
    cloud_anom_err = _score_windows_np(x_anom, params, mean, std)
    m_norm, m_anom = len(cloud_norm_err), len(cloud_anom_err)
    edge_norm, edge_anom = edge_norm[:m_norm], edge_anom[:m_anom]
    labels = labels[:m_anom]
    cloud_norm = cloud_norm_err > threshold
    cloud_anom = cloud_anom_err > threshold

    # Two-stage confirm = edge flagged AND cloud confirmed.
    two_norm = edge_norm & cloud_norm
    two_anom = edge_anom & cloud_anom

    def _prf(tp, fp, fn):
        prec = tp / max(tp + fp, 1)
        rec = tp / max(tp + fn, 1)
        f1 = 2 * prec * rec / max(prec + rec, 1e-9)
        return round(prec, 4), round(rec, 4), round(f1, 4)

    edge_p, edge_r, edge_f = _prf(edge_anom.sum(), edge_norm.sum(), (~edge_anom).sum())
    two_p, two_r, two_f = _prf(two_anom.sum(), two_norm.sum(), (~two_anom).sum())

    report = {
        "cloud_model_version": args.version,
        "window": WINDOW,
        "cloud_threshold": round(threshold, 6),
        "test_normal": m_norm,
        "test_anomalies": m_anom,
        "edge_only": {
            "precision": edge_p, "recall": edge_r, "f1": edge_f,
            "false_positives": int(edge_norm.sum()),
        },
        "two_stage_edge_then_cloud": {
            "precision": two_p, "recall": two_r, "f1": two_f,
            "false_positives": int(two_norm.sum()),
        },
        "edge_fp_suppressed_by_cloud": int(edge_norm.sum() - two_norm.sum()),
        "true_anomalies_dropped_by_cloud": int(edge_anom.sum() - two_anom.sum()),
        "recall_by_type": {
            k: {
                "count": int((labels == k).sum()),
                "edge_recall": round(float(edge_anom[labels == k].mean()), 4),
                "two_stage_recall": round(float(two_anom[labels == k].mean()), 4),
            }
            for k in sorted(set(labels.tolist()))
        },
        "evaluated_at": datetime.now(UTC).isoformat(),
    }
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / "offline_evaluation.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== Two-stage detection quality (edge IF -> cloud LSTM-AE) ===")
    print(f"  edge only : P={edge_p} R={edge_r} F1={edge_f}  FP={int(edge_norm.sum())}")
    print(f"  two-stage : P={two_p} R={two_r} F1={two_f}  FP={int(two_norm.sum())}")
    print(f"  edge false positives suppressed by cloud: {report['edge_fp_suppressed_by_cloud']}")
    print(f"  true anomalies dropped by cloud         : {report['true_anomalies_dropped_by_cloud']}")
    print(f"Report -> {path}")


if __name__ == "__main__":
    raise SystemExit(main())

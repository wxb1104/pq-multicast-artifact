#!/usr/bin/env python3
"""fig2_crypto.py - cryptographic profile: signature size and verify latency."""
import sys, pandas as pd, matplotlib.pyplot as plt
sys.path.insert(0, "/mnt/e/pqc+zhengshu/pq-net-research/experiments/sim")
from figs_common import ROOT, clean_ax, save

df = pd.read_csv(f"{ROOT}/results/local/crypto_bench_local.csv")
order = ["Ed25519", "ML-DSA-44", "ML-DSA-65", "ML-DSA-87", "Falcon-padded-512",
         "SLH-DSA-128s", "SLH-DSA-128f", "SLH-DSA-192f", "SLH-DSA-256f"]
labels = {"Falcon-padded-512": "Falcon-512"}
colors = {
    "Ed25519": "#5a5a5a", "ML-DSA-44": "#0072B2", "ML-DSA-65": "#56B4E9",
    "ML-DSA-87": "#1b4f72", "Falcon-padded-512": "#E69F00",
    "SLH-DSA-128s": "#006d4c", "SLH-DSA-128f": "#009E73",
    "SLH-DSA-192f": "#5ab489", "SLH-DSA-256f": "#93cfae",
}
df = df.set_index("scheme").loc[order].reset_index()
names = [labels.get(s, s) for s in order]
y = list(range(len(order)))[::-1]

fig, axes = plt.subplots(1, 2, figsize=(170 / 25.4, 62 / 25.4), sharey=True)

def bars(ax, col, title, fmt):
    vals = df[col].values
    ax.barh(y, vals, color=[colors[s] for s in order], edgecolor="white", height=0.66)
    ax.set_xscale("log")
    ax.set_xlabel(title)
    xmax = max(vals)
    for yi, v in zip(y, vals):
        ax.text(v * 1.08, yi, fmt(v), va="center", ha="left", fontsize=6.3)
    ax.set_xlim(20, xmax * 2.4)
    clean_ax(ax)

bars(axes[0], "sig_bytes", "Signature size (bytes, log)", lambda v: f"{int(v)}")
bars(axes[1], "verify_us", "Verification time ($\\mu$s, log)", lambda v: f"{v:.0f}")
axes[0].set_yticks(y); axes[0].set_yticklabels(names)
fig.align_xlabels(axes)
fig.tight_layout(pad=0.4)
save(fig, "fig2_crypto")

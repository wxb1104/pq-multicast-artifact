"""figs_common.py - shared style, paths and helpers for P5 experimental figures."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = "/mnt/e/pqc+zhengshu/pq-net-research"
NS = f"{ROOT}/results/local/ns3"
FIGS = f"{ROOT}/paper/figs"

# Okabe-Ito
OI = {
    "black": "#000000", "orange": "#E69F00", "sky": "#56B4E9", "green": "#009E73",
    "yellow": "#F0E442", "blue": "#0072B2", "verm": "#D55E00", "purple": "#CC79A7",
}

SIGNAME = {
    64: "Ed25519", 666: "Falcon-512", 2420: "ML-DSA-44", 3309: "ML-DSA-65",
    4627: "ML-DSA-87", 7856: "SLH-DSA-128s", 17088: "SLH-DSA-128f",
    35664: "SLH-DSA-192f", 49856: "SLH-DSA-256f",
}

plt.rcParams.update({
    "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7.2,
    "ytick.labelsize": 7.2, "legend.fontsize": 6.8, "axes.linewidth": 0.8,
    "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "xtick.major.size": 2.6, "ytick.major.size": 2.6, "lines.linewidth": 1.3,
    "figure.dpi": 150,
})

def clean_ax(ax):
    ax.grid(False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

def load_ci(name):
    return pd.read_csv(f"{NS}/{name}_ci.csv")

def get_row(df, metric, **kv):
    """Return (mean, halfci) for the first ci row matching metric and kv."""
    m = df[df["metric"] == metric]
    for k, v in kv.items():
        m = m[m[k] == v]
    if m.empty:
        return None, None
    r = m.iloc[0]
    return float(r["mean"]), float(r["halfci"])

def series(df, metric, xkey, fixed):
    """Return x[], mean[], halfci[] for rows matching metric and fixed dict."""
    m = df[df["metric"] == metric]
    for k, v in fixed.items():
        m = m[m[k] == v]
    m = m.sort_values(xkey)
    return (m[xkey].tolist(), m["mean"].tolist(),
            m["halfci"].fillna(0).tolist())

def save(fig, base):
    fig.savefig(f"{FIGS}/{base}.pdf", bbox_inches="tight", pad_inches=0.01)
    fig.savefig(f"{FIGS}/{base}.png", dpi=300, bbox_inches="tight", pad_inches=0.01)
    plt.close(fig)
    print(f"{base} done")

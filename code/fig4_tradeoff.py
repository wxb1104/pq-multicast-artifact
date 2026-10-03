#!/usr/bin/env python3
"""fig4_tradeoff.py - latency vs joint authentication for the three strategies."""
import sys
sys.path.insert(0, "/mnt/e/pqc+zhengshu/pq-net-research/experiments/sim")
import matplotlib.pyplot as plt
from figs_common import load_ci, clean_ax, save, SIGNAME

ci = load_ci("E9_baseline")
def pt(mode, fecR, sig, metric):
    m = ci[(ci["metric"] == metric) & (ci["mode"] == mode) &
           (ci["fecR"] == fecR) & (ci["sigSize"] == sig)]
    r = m.iloc[0]
    return float(r["mean"]), float(r["halfci"]) if r["halfci"] == r["halfci"] else 0.0

sigs = [64, 666, 2420, 3309, 4627, 7856, 17088, 35664, 49856]

fig, ax = plt.subplots(figsize=(135 / 25.4, 78 / 25.4))

def collect(mode, fecR):
    xs, xe, ys, ye = [], [], [], []
    for s in sigs:
        x, xh = pt(mode, fecR, s, "medMs")
        y, yh = pt(mode, fecR, s, "jointFrac")
        xs.append(x); xe.append(xh); ys.append(y); ye.append(yh)
    return xs, xe, ys, ye

# chain
xs, xe, ys, ye = collect("chain", 0.25)
ax.errorbar(xs, ys, xerr=xe, yerr=ye, fmt="s", color="#0072B2", ms=5, capsize=2.2,
            ls="none", label="Connected chain")
# fec
xs2, xe2, ys2, ye2 = collect("fec", 0.5)
ax.errorbar(xs2, ys2, xerr=xe2, yerr=ye2, fmt="o", color="#009E73", ms=5,
            capsize=2.2, ls="none", label="Chain + FEC ($\\rho=0.5$)")
# persig (Ed only)
px, pxh = pt("persig", 0.25, 64, "medMs")
py, pyh = pt("persig", 0.25, 64, "jointFrac")
ax.errorbar([px], [py], xerr=[pxh], yerr=[pyh], fmt="^", color="#E69F00", ms=7,
            capsize=2.2, ls="none", label="Per-packet signing")

# arrow for SLH-256f chain -> fec
ic = sigs.index(49856)
ax.annotate("", xy=(xs2[ic], ys2[ic]), xytext=(xs[ic], ys[ic]),
            arrowprops=dict(arrowstyle="-|>", color="#888888", lw=1.2,
                            connectionstyle="arc3,rad=-0.18"))
ax.text(xs[ic] * 1.05, ys[ic] - 0.018, "SLH-DSA-256f", fontsize=6.2, ha="left")
ax.text(xs2[ic] * 0.6, ys2[ic] + 0.02, "SLH-DSA-256f + FEC", fontsize=6.2,
        ha="right", color="#1d5a31")
# Ed labels
ax.text(xs[0] * 1.12, ys[0] - 0.03, "Ed25519", fontsize=6.2)
# persig annotation
ax.text(px * 1.4, py - 0.045, "immediate, but $n$ verifications/block",
        fontsize=6.2, color="#9a6a1a")
ax.text(0.98, 0.05, "chain and FEC: 1 verification/block", fontsize=6.2,
        transform=ax.transAxes, ha="right", color="#444444")

ax.set_xscale("log")
ax.set_xlabel("Median authenticated-block latency (ms, log)")
ax.set_ylabel("Authenticated blocks (joint)")
ax.set_xlim(0.04, 3000); ax.set_ylim(-0.03, 0.32)
clean_ax(ax); ax.legend(frameon=False, loc="upper left")
fig.tight_layout(pad=0.4)
save(fig, "fig4_tradeoff")

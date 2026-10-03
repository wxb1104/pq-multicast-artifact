#!/usr/bin/env python3
"""fig6_burst.py - burst-loss: conditional auth and p95 latency for SLH-DSA-128f."""
import sys
sys.path.insert(0, "/mnt/e/pqc+zhengshu/pq-net-research/experiments/sim")
import matplotlib.pyplot as plt
from figs_common import load_ci, clean_ax, save

ci = load_ci("E7_burst")
SIG = 17088
def ser(mode, ileave, metric):
    m = ci[(ci.metric == metric) & (ci.sigSize == SIG) & (ci["mode"] == mode) &
           (ci.ileave == ileave)].sort_values("burstLen")
    return m["burstLen"].tolist(), m["mean"].tolist(), m["halfci"].fillna(0).tolist()

fig, axes = plt.subplots(1, 2, figsize=(170/25.4, 64/25.4))
specs = [
    ("chain", 0, "s", "-",  "#0072B2", "Chain, no FEC"),
    ("fec",   0, "o", "--", "#009E73", "FEC, no interleaving"),
    ("fec",   4, "^", ":",  "#5ab489", "FEC, interleave $I=4$"),
    ("fec",   8, "v", "-.", "#93cfae", "FEC, interleave $I=8$"),
]
for ax, metric, yl in ((axes[0], "condFrac", "Conditional authentication"),
                       (axes[1], "p95Ms", "p95 latency (ms)")):
    for mode, il, mk, ls, c, lab in specs:
        x, y, h = ser(mode, il, metric)
        ax.errorbar(x, y, yerr=h, fmt=mk, color=c, ms=4.2, capsize=2.2, ls=ls,
                    lw=1.1, label=lab)
    ax.set_xlabel("Mean burst length (packets)")
    ax.set_ylabel(yl)
    clean_ax(ax)
axes[0].set_ylim(0.3, 1.05)
axes[1].set_yscale("log")
axes[0].legend(frameon=False, loc="lower right")
fig.tight_layout(pad=0.5)
save(fig, "fig6_burst")

#!/usr/bin/env python3
"""fig8_sensitivity.py - deployment sensitivity: rate/RTT, group size, chunk size."""
import sys
sys.path.insert(0, "/mnt/e/pqc+zhengshu/pq-net-research/experiments/sim")
import numpy as np
import matplotlib.pyplot as plt
from figs_common import load_ci, clean_ax, save, SIGNAME

fig, axes = plt.subplots(1, 3, figsize=(170/25.4, 58/25.4))

# (a) E4 median latency vs rate, aggregated over RTT, chain vs fec
e4 = load_ci("E4_rttrate")
rates = ["100Mbps", "10Mbps", "1Mbps"]
x = np.arange(3)
for j, (mode, c) in enumerate([("chain", "#0072B2"), ("fec", "#009E73")]):
    vals = []
    for r in rates:
        m = e4[(e4.metric == "medMs") & (e4.rate == r) & (e4["mode"] == mode)]
        vals.append(m["mean"].mean())
    axes[0].bar(x + (j - 0.5) * 0.36, vals, width=0.34, color=c,
                label="Chain" if mode == "chain" else "FEC")
axes[0].set_yscale("log")
axes[0].set_xticks(x); axes[0].set_xticklabels(["100M", "10M", "1M"])
axes[0].set_xlabel("Last-mile rate"); axes[0].set_ylabel("Median latency (ms, log)")
axes[0].set_title("(a) Rate (RTT aggregated)", fontsize=7.4); clean_ax(axes[0])
axes[0].legend(frameon=False)

# (b) E2 joint vs group size
e2 = load_ci("E2_scale")
for mode, mk, c, ls in [("chain", "s", "#0072B2", "-"), ("fec", "o", "#009E73", "--")]:
    m = e2[(e2.metric == "jointFrac") & (e2["mode"] == mode)].sort_values("M")
    axes[1].errorbar(m["M"], m["mean"], yerr=m["halfci"].fillna(0), fmt=mk, color=c,
                     ms=4.2, capsize=2.2, ls=ls, lw=1.0,
                     label="Chain" if mode == "chain" else "FEC")
axes[1].set_xscale("log")
axes[1].set_xlabel("Group size $M$"); axes[1].set_ylabel("Authenticated blocks (joint)")
axes[1].set_title("(b) Group scalability", fontsize=7.4); clean_ax(axes[1])
axes[1].set_ylim(0, 0.28)
axes[1].legend(frameon=False, loc="upper right")

# (c) E10 cond vs chunk C for three schemes
e10 = load_ci("E10_chunkC")
Cs = [1280, 1350, 1400]
x = np.arange(3)
schs = [(64, "#5a5a5a"), (4627, "#1b4f72"), (49856, "#7d3c98")]
for j, (sig, c) in enumerate(schs):
    vals = []
    for C in Cs:
        m = e10[(e10.metric == "condFrac") & (e10.sigSize == sig) & (e10.chunkC == C)]
        vals.append(float(m.iloc[0]["mean"]))
    axes[2].bar(x + (j - 1) * 0.26, vals, width=0.24, color=c, label=SIGNAME[sig])
axes[2].set_xticks(x); axes[2].set_xticklabels(["1280", "1350", "1400"])
axes[2].set_xlabel("Chunk size $C$ (bytes)")
axes[2].set_ylabel("Conditional authentication")
axes[2].set_ylim(0.9, 1.01)
axes[2].set_title("(c) MTU conservatism", fontsize=7.4); clean_ax(axes[2])
axes[2].legend(frameon=False, loc="lower left")

fig.tight_layout(pad=0.5)
save(fig, "fig8_sensitivity")

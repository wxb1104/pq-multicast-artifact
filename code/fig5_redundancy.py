#!/usr/bin/env python3
"""fig5_redundancy.py - conditional authentication vs FEC redundancy at p=0.1."""
import sys, math
sys.path.insert(0, "/mnt/e/pqc+zhengshu/pq-net-research/experiments/sim")
import matplotlib.pyplot as plt
from math import comb
from figs_common import load_ci, clean_ax, save, SIGNAME

p, n = 0.1, 32
def Msig(s): return s + 8*32 + 8
def ks_(s, C=1400): return max(1, math.ceil(Msig(s)/C))
def cf_cond(s, rho, C=1400):
    ks = ks_(s, C); ncc = ks + math.ceil(rho * ks)
    return sum(comb(ncc, i) * (1-p)**i * p**(ncc-i) for i in range(ks, ncc+1))

ci = load_ci("E5_redundancy")
fig, ax = plt.subplots(figsize=(120/25.4, 72/25.4))
schs = [(2420, "s", "#0072B2"), (4627, "D", "#1b4f72"),
        (7856, "^", "#CC79A7"), (17088, "v", "#D55E00")]
rho_grid = [i/100 for i in range(0, 101, 2)]
for s, mk, c in schs:
    m = ci[(ci.metric == "condFrac") & (ci.sigSize == s)].sort_values("fecR")
    ax.errorbar(m["fecR"], m["mean"], yerr=m["halfci"].fillna(0), fmt=mk, color=c,
                ms=4.4, capsize=2.2, ls="-", lw=1.0, label=SIGNAME[s])
    ax.plot(rho_grid, [cf_cond(s, r) for r in rho_grid], "--", color=c, lw=0.8,
            alpha=0.75)
ax.axhline(0.99, color="#999999", lw=0.8, ls=":")
ax.text(0.01, 1.005, "target 0.99", fontsize=6.0, color="#777777")
ax.set_xlabel("FEC redundancy ratio $\\rho$")
ax.set_ylabel("Conditional authentication $\\Pr[S_i\\mid D_i]$")
ax.set_ylim(0.1, 1.06); clean_ax(ax)
ax.legend(frameon=False, loc="lower right")
ax.text(0.56, 0.12, "dashed: closed form", fontsize=6.2, color="#666666",
        transform=ax.transAxes)
fig.tight_layout(pad=0.4)
save(fig, "fig5_redundancy")

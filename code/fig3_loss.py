#!/usr/bin/env python3
"""fig3_loss.py - joint block authentication vs loss, simulation vs closed form."""
import sys, math
sys.path.insert(0, "/mnt/e/pqc+zhengshu/pq-net-research/experiments/sim")
import matplotlib.pyplot as plt
from math import comb
from figs_common import load_ci, clean_ax, save, SIGNAME

n = 32
def Msig(sig): return sig + 8 * 32 + 8
def kchain(sig): return math.ceil((Msig(sig) + 64) / 1480)
def cf_chain(sig, p): return (1 - p) ** (n + kchain(sig))
def ks_(sig, C=1400): return max(1, math.ceil(Msig(sig) / C))
def nc_(sig, rho, C=1400):
    ks = ks_(sig, C); return ks, ks + math.ceil(rho * ks)
def PrS(sig, p, rho, C=1400):
    ks, ncc = nc_(sig, rho, C)
    return sum(comb(ncc, i) * (1 - p) ** i * p ** (ncc - i) for i in range(ks, ncc + 1))
def cf_fec(sig, p, rho): return (1 - p) ** n * PrS(sig, p, rho)

ci = load_ci("E3_loss")
def sim_series(mode, fecR, sig):
    m = ci[(ci["metric"] == "jointFrac") & (ci["mode"] == mode) &
           (ci["fecR"] == fecR) & (ci["sigSize"] == sig)].sort_values("loss")
    return m["loss"].tolist(), m["mean"].tolist(), m["halfci"].fillna(0).tolist()

fig, axes = plt.subplots(1, 2, figsize=(170 / 25.4, 66 / 25.4))

# (a) chain
ax = axes[0]
chain_schs = [(64, "o", "#5a5a5a"), (2420, "s", "#0072B2"),
              (4627, "D", "#1b4f72"), (7856, "^", "#CC79A7"),
              (17088, "v", "#D55E00"), (49856, "P", "#7d3c98")]
pgrid = [i / 1000 for i in range(0, 201, 2)]
for sig, mk, c in chain_schs:
    x, y, h = sim_series("chain", 0.25, sig)
    ax.errorbar(x, y, yerr=h, fmt=mk, color=c, ms=4.2, capsize=2.2, ls="-", lw=1.0,
                label=SIGNAME[sig])
    ax.plot(pgrid, [cf_chain(sig, p) for p in pgrid], "--", color=c, lw=0.9)
ax.set_xlabel("Independent last-mile loss $p$")
ax.set_ylabel("Authenticated blocks (joint)")
ax.set_title("(a) Connected chain, no FEC", fontsize=7.6)
ax.set_ylim(-0.02, 1.02); clean_ax(ax)
ax.legend(ncol=2, frameon=False, handlelength=2.0, columnspacing=1.0, loc="upper right")
ax.plot([], [], "--", color="#888888", label="closed form")
ax.text(0.02, 0.05, "dashed: closed form", fontsize=6.2, transform=ax.transAxes,
        color="#666666")

# (b) FEC rho=.5
ax = axes[1]
ax.plot(pgrid, [(1 - p) ** n for p in pgrid], "-", color="#111111", lw=1.6,
        label="data-complete $(1-p)^n$")
fec_schs = [(64, "o", "#5a5a5a"), (4627, "D", "#1b4f72"), (49856, "P", "#7d3c98")]
for sig, mk, c in fec_schs:
    x, y, h = sim_series("fec", 0.5, sig)
    ax.errorbar(x, y, yerr=h, fmt=mk, color=c, ms=4.4, capsize=2.2, ls="none",
                label=SIGNAME[sig])
ax.set_xlabel("Independent last-mile loss $p$")
ax.set_title("(b) Connected chain + FEC ($\\rho=0.5$)", fontsize=7.6)
ax.set_ylim(-0.02, 1.02); clean_ax(ax)
ax.legend(frameon=False, loc="upper right")

fig.tight_layout(pad=0.5)
save(fig, "fig3_loss")

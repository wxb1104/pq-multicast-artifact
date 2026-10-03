#!/usr/bin/env python3
"""fig7_blocksize.py - joint and conditional authentication vs block size."""
import sys, math
sys.path.insert(0, "/mnt/e/pqc+zhengshu/pq-net-research/experiments/sim")
import matplotlib.pyplot as plt
from math import comb
from figs_common import load_ci, clean_ax, save

ci = load_ci("E8_blocksize")
loss = 0.05
def Msig(s): return s + 8*32 + 8
def kchain(s): return math.ceil((Msig(s)+64)/1480)
def cf_chain_cond(s): return (1-loss)**kchain(s)
def cf_fec_cond(s, rho=0.25, C=1400):
    ks = max(1, math.ceil(Msig(s)/C)); ncc = ks + math.ceil(rho*ks)
    return sum(comb(ncc, i)*(1-loss)**i*loss**(ncc-i) for i in range(ks, ncc+1))
def ser(sig, mode, metric):
    m = ci[(ci.metric == metric) & (ci.sigSize == sig) & (ci["mode"] == mode) &
           (ci.loss == loss)].sort_values("n")
    return m["n"].tolist(), m["mean"].tolist(), m["halfci"].fillna(0).tolist()

fig, axes = plt.subplots(1, 2, figsize=(170/25.4, 62/25.4))
ngrid = list(range(4, 130))
# (a) joint
ax = axes[0]
ax.plot(ngrid, [(1-loss)**nn for nn in ngrid], "-", color="#111111", lw=1.6,
        label="data-complete $(1-p)^n$")
for sig, mk, c, lab in [(64, "o", "#5a5a5a", "Chain Ed25519"),
                        (17088, "v", "#D55E00", "Chain SLH-DSA-128f")]:
    x, y, h = ser(sig, "chain", "jointFrac")
    ax.errorbar(x, y, yerr=h, fmt=mk, color=c, ms=4.2, capsize=2.2, ls="-", lw=1.0,
                label=lab)
x, y, h = ser(17088, "fec", "jointFrac")
ax.errorbar(x, y, yerr=h, fmt="^", color="#009E73", ms=4.4, capsize=2.2, ls="--",
            lw=1.0, label="FEC SLH-DSA-128f")
ax.set_xlabel("Packets per block $n$"); ax.set_ylabel("Authenticated blocks (joint)")
ax.set_title("(a) Joint authentication", fontsize=7.6); clean_ax(ax)
ax.legend(frameon=False, loc="upper right")
# (b) conditional: closed form is independent of n; sim reliable only for n<=64
ax = axes[1]
for sig, c, cf in [(64, "#5a5a5a", cf_chain_cond(64)),
                   (17088, "#D55E00", cf_chain_cond(17088))]:
    ax.axhline(cf, color=c, lw=0.9, ls=":", alpha=0.9)
for sig, mk, c, ls, lab in [(64, "o", "#5a5a5a", "-", "Chain Ed25519"),
                            (17088, "v", "#D55E00", "-", "Chain SLH-DSA-128f")]:
    x, y, h = ser(sig, "chain", "condFrac")
    x, y, h = x[:4], y[:4], h[:4]
    ax.errorbar(x, y, yerr=h, fmt=mk, color=c, ms=4.2, capsize=2.2, ls=ls, lw=1.0,
                label=lab)
x, y, h = ser(17088, "fec", "condFrac")
ax.axhline(cf_fec_cond(17088), color="#009E73", lw=0.9, ls=":", alpha=0.9)
ax.errorbar(x[:4], y[:4], yerr=h[:4], fmt="^", color="#009E73", ms=4.4, capsize=2.2,
            ls="--", lw=1.0, label="FEC SLH-DSA-128f")
ax.set_xlabel("Packets per block $n$")
ax.set_ylabel("Conditional authentication")
ax.set_title("(b) Conditional authentication", fontsize=7.6); clean_ax(ax)
ax.set_ylim(0.3, 1.05)
ax.legend(frameon=False, loc="lower left")
ax.text(0.98, 0.78, "dotted: closed form, independent of $n$", fontsize=6.0,
        transform=ax.transAxes, ha="right", color="#666666")
fig.tight_layout(pad=0.5)
save(fig, "fig7_blocksize")

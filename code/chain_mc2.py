#!/usr/bin/env python3
"""chain_mc2.py - chain-graph Monte Carlo vs closed forms.

Large block counts and repeated trials; reports mean and 95% t-CI for
data completion, signature availability (conditional), and the joint
delivered+authenticated probability, under independent and burst loss.
"""
import math, os
import numpy as np
from scipy.stats import binom, t

OUT = "/mnt/e/pqc+zhengshu/pq-net-research/results/local"
os.makedirs(OUT, exist_ok=True)

H = 32          # hash bytes
T = 8           # signature-record hash links
KID = 8         # key id bytes
IP_PAY = 1480   # Ethernet IPv4 UDP-ish payload used for fragment count
FEC_C = 1400

# scheme: (sig bytes, pk bytes)
SCHEMES = {
    "Ed25519":            (64, 32),
    "ML-DSA-44":          (2420, 1312),
    "ML-DSA-65":          (3309, 1952),
    "ML-DSA-87":          (4627, 2592),
    "Falcon-padded-512":  (666, 897),
    "Falcon-512":         (752, 897),
    "SLH-DSA-128f":       (17088, 32),
    "SLH-DSA-128s":       (7856, 32),
    "SLH-DSA-192f":       (35664, 64),
    "SLH-DSA-256f":       (49856, 64),
}

def Msigma(sig):
    return sig + T*H + KID

def frag_k(sig):
    return max(1, math.ceil((Msigma(sig) + 64) / IP_PAY))

def fec_counts(sig, rho, C=FEC_C):
    ks = max(1, math.ceil(Msigma(sig) / C))
    nc = ks + math.ceil(rho*ks)
    return ks, nc

def fec_recover(sig, p, rho, C=FEC_C):
    ks, nc = fec_counts(sig, rho, C)
    return float(binom.sf(ks-1, nc, 1-p)), ks, nc

def ci(arr):
    a = np.asarray(arr, float)
    m = a.mean()
    if len(a) < 2:
        return m, 0.0
    se = a.std(ddof=1)/math.sqrt(len(a))
    return m, t.ppf(0.975, len(a)-1)*se

# ---------------- independent loss Monte Carlo ----------------
def mc_indep(sig, p, n, rho, nb, rng):
    """One trial over nb blocks. Returns (data_frac, cond_sig, joint)."""
    k = frag_k(sig)
    ks, nc = fec_counts(sig, rho) if rho is not None else (0, 0)
    data = rng.random((nb, n)) >= p
    data_ok = data.all(axis=1)
    # chain: k independent fragments; fec: nc coded packets, need ks
    if rho is None:
        sigp = (rng.random((nb, k)) >= p).all(axis=1)
    else:
        coded = rng.random((nb, nc)) >= p
        sigp = coded.sum(axis=1) >= ks
    both = data_ok & sigp
    d = data_ok.mean()
    cond = both.sum()/data_ok.sum() if data_ok.sum() else float("nan")
    return d, (0.0 if data_ok.sum()==0 else cond), both.mean()

def run_indep(n=32, nb=2000, reps=40):
    ps = [0.0, 0.02, 0.05, 0.10, 0.15, 0.20]
    rows = []
    rng = np.random.default_rng(20261003)
    for name,(sig,pk) in SCHEMES.items():
        k = frag_k(sig)
        for p in ps:
            for carry,rho in (("chain",None),("fec025",0.25),("fec050",0.50)):
                ds,cs,js=[],[],[]
                for _ in range(reps):
                    d,c,j = mc_indep(sig,p,n,rho,nb,rng)
                    ds.append(d); cs.append(c); js.append(j)
                dm,dcix = ci(ds); cm,ccix = ci(cs); jm,jcix = ci(js)
                # closed forms
                cf_data = (1-p)**n
                if rho is None:
                    cf_cond = (1-p)**k
                else:
                    cf_cond,_,_ = fec_recover(sig,p,rho)
                cf_joint = cf_data*cf_cond
                rows.append(dict(scheme=name,carry=carry,p=p,n=n,
                    cf_data=cf_data,mc_data=dm,data_halfci=dcix,
                    cf_cond=cf_cond,mc_cond=cm,cond_halfci=ccix,
                    cf_joint=cf_joint,mc_joint=jm,joint_halfci=jcix))
    import pandas as pd
    df = pd.DataFrame(rows)
    df.to_csv(f"{OUT}/mc_indep.csv", index=False)
    # validation: closed form inside MC CI?
    def inside(cf,mc,h):
        return abs(cf-mc) <= h + 1e-9
    ok_d = sum(inside(r["cf_data"],r["mc_data"],r["data_halfci"]) for r in rows)
    ok_c = sum(inside(r["cf_cond"],r["mc_cond"],r["cond_halfci"]) for r in rows)
    ok_j = sum(inside(r["cf_joint"],r["mc_joint"],r["joint_halfci"]) for r in rows)
    N=len(rows)
    print(f"[indep] closed-form within 95% CI: data {ok_d}/{N}, cond {ok_c}/{N}, joint {ok_j}/{N}")
    return df

# ---------------- burst (Gilbert-Elliott) ----------------
def ge_series(npackets, mean_loss, burst_len, rng):
    """Return boolean array True=received for a GE two-state channel."""
    pbg = 1.0/burst_len
    PB = min(mean_loss, 0.999)
    pgb = PB/(1-PB)*pbg
    bad = False; out = np.zeros(npackets, bool)
    u = rng.random(npackets)
    for i in range(npackets):
        bad = (u[i] < pgb) if not bad else (u[i] >= pbg)
        out[i] = not bad
    return out

def mc_burst_one(sig, mean_loss, burst_len, n, rho, ileave, nb, rng):
    k = frag_k(sig); ks,nc = fec_counts(sig, rho if rho is not None else 0.25)
    # lay out the wire sequence per block: n data then signature packets
    sig_n = k if rho is None else nc
    seq = np.ones(nb*(n+sig_n), bool)
    recv = ge_series(len(seq), mean_loss, burst_len, rng)
    recv = recv.reshape(nb, n+sig_n)
    data_ok = recv[:, :n].all(axis=1)
    if rho is None:
        sigp = recv[:, n:].all(axis=1)
    else:
        if ileave == 0:
            sigp = recv[:, n:].sum(axis=1) >= ks
        else:
            # interleaved coded packets spread to later blocks; gather by a
            # sliding window of ileave blocks (decode uses window of coded pkts)
            coded = recv[:, n:].copy()
            # spread: coded packet m of block b lands in b+1+floor(m*ileave/sig_n)
            landed = np.zeros((nb+ileave+1, sig_n), bool)
            for b in range(nb):
                for m in range(sig_n):
                    tgt = b + (1 + int(math.floor(m*ileave/sig_n)))
                    if tgt < landed.shape[0]:
                        landed[tgt, m] = coded[b, m]
            # block b decodes using coded packets whose landing window covers b
            sigp = np.zeros(nb, bool)
            for b in range(nb):
                lo = max(0, b-ileave-1)
                window = landed[lo:b+1].reshape(-1)
                sigp[b] = window.sum() >= ks
    both = data_ok & sigp
    d = data_ok.mean()
    c = both.sum()/data_ok.sum() if data_ok.sum() else float("nan")
    return d, (0.0 if data_ok.sum()==0 else c), both.mean()

def run_burst(n=32, nb=2000, reps=30):
    import pandas as pd
    rows=[]
    rng = np.random.default_rng(77123)
    targets = [("ML-DSA-44",2420),("SLH-DSA-128f",17088),("Ed25519",64)]
    for name,sig in targets:
        for bl in [2,5,10,20]:
            for carry,rho,I in (("chain",None,0),("fec_clust",0.5,0),
                                ("fec_I4",0.5,4),("fec_I8",0.5,8)):
                ds,cs,js=[],[],[]
                for _ in range(reps):
                    d,c,j = mc_burst_one(sig,0.10,bl,n,rho,I,nb,rng)
                    ds.append(d);cs.append(c);js.append(j)
                dm,dx=ci(ds);cm,cx=ci(cs);jm,jx=ci(js)
                rows.append(dict(scheme=name,carry=carry,burst_len=bl,ileave=I,
                    mc_data=dm,data_halfci=dx,mc_cond=cm,cond_halfci=cx,
                    mc_joint=jm,joint_halfci=jx))
    df=pd.DataFrame(rows); df.to_csv(f"{OUT}/mc_burst.csv",index=False)
    print(f"[burst] wrote {len(df)} rows")
    return df

if __name__ == "__main__":
    run_indep()
    run_burst()
    print("MC done ->", OUT)

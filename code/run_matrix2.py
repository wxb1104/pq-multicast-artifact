#!/usr/bin/env python3
"""run_matrix2.py - full ns-3.41 packet-simulation matrix (pqmc2).

Runs every deployment experiment over multiple RNG seeds, aggregates across
seeds with 95% t-CIs, and writes one CSV per experiment. Independent runs
execute in a process pool.
"""
import subprocess, os, math, sys
import numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor

ROOT = "/mnt/e/pqc+zhengshu/pq-net-research"
BIN  = f"{ROOT}/experiments/sim/pqmc2"
OUT  = f"{ROOT}/results/local/ns3"
os.makedirs(OUT, exist_ok=True)

SIG = {  # signature wire size (bytes), local liboqs 0.16
    "Ed25519":64, "ML-DSA-44":2420, "ML-DSA-65":3309, "ML-DSA-87":4627,
    "Falcon-padded-512":666,
    "SLH-DSA-128f":17088, "SLH-DSA-128s":7856,
    "SLH-DSA-192f":35664, "SLH-DSA-256f":49856,
}
# verify microseconds measured on the local host (fallback; CSV overrides)
VERIFY = {
    "Ed25519":71.4,"ML-DSA-44":51.1,"ML-DSA-65":80.0,"ML-DSA-87":128.4,
    "Falcon-padded-512":28.1,
    "SLH-DSA-128f":1021.2,"SLH-DSA-128s":386.6,
    "SLH-DSA-192f":1606.1,"SLH-DSA-256f":1626.9,
}
def load_local_verify():
    p = f"{ROOT}/results/local/crypto_bench_local.csv"
    if not os.path.exists(p):
        print("verify source: built-in (local bench absent)"); return
    df = pd.read_csv(p)
    got=0
    for _,r in df.iterrows():
        nm=r.get("scheme")
        if nm in VERIFY and pd.notna(r.get("verify_us")):
            VERIFY[nm]=float(r["verify_us"]); got+=1
    print(f"verify source: local bench ({got} schemes)")

COLS=["tag","mode","M","n","d","sigSize","loss","rttMs","rate","chunkC",
      "fecR","ileave","burstLen","seed","range","dataComp","sigAvail","both",
      "dataFrac","condFrac","jointFrac","rxBytes","verifies","medMs","p95Ms",
      "verifyLoad","cpuFrac"]
INTS={"M","n","d","sigSize","rttMs","chunkC","ileave","seed"}

def one(cfg):
    args=[BIN]
    for k,v in cfg.items():
        args.append(f"--{k}={v}")
    for attempt in range(2):
        try:
            out=subprocess.run(args,capture_output=True,text=True,timeout=300)
            line=[l for l in out.stdout.strip().splitlines() if "," in l]
            if line:
                vals=line[-1].split(",")
                d=dict(zip(COLS,vals))
                for c in COLS:
                    if c in INTS: d[c]=int(float(d[c]))
                    elif c not in ("mode","rate","tag"): d[c]=float(d[c])
                return d
        except Exception as e:
            if attempt==1: return {"tag":cfg.get("tag"),"error":str(e)}
    return {"tag":cfg.get("tag"),"error":"no output"}

def base(scheme, seed, mode, tag, **kw):
    d=dict(sigSize=SIG[scheme],verifyUs=VERIFY[scheme],M=10,n=32,d=3,t=8,
           blocks=40,payload=1200,loss=0.0,rttMs=20,lastRate="10Mbps",
           mode=mode,tag=tag,seed=seed,chunkC=1400,fecR=0.25,burst=0,
           burstLen=5,ileave=0)
    d.update(kw); return d

def run_cfgs(cfgs, workers, fname, groupkeys, meankeys):
    print(f"[{fname}] {len(cfgs)} runs")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        rows=list(ex.map(one,cfgs))
    bad=[r for r in rows if "error" in r]
    if bad: print("  FAILURES:",len(bad),bad[:3])
    df=pd.DataFrame([r for r in rows if "error" not in r])
    df.to_csv(f"{OUT}/{fname}_raw.csv",index=False)
    if df.empty:
        print("  NO VALID ROWS; aborting this experiment")
        return df
    # aggregate across seeds
    agg=df.groupby(groupkeys)[meankeys].agg(["mean","std","count"]).reset_index()
    agg.to_csv(f"{OUT}/{fname}.csv",index=False)
    # tidy long form with half CI
    recs=[]
    for keys,g in df.groupby(groupkeys):
        keys=keys if isinstance(keys,tuple) else (keys,)
        for mk in meankeys:
            x=g[mk].values
            m=x.mean()
            h=(x.std(ddof=1)/math.sqrt(len(x))*1.96) if len(x)>1 else 0
            recs.append(dict(zip(groupkeys,keys),metric=mk,mean=m,halfci=h,reps=len(x)))
    pd.DataFrame(recs).to_csv(f"{OUT}/{fname}_ci.csv",index=False)
    print(f"  wrote {fname}: {df.shape[0]} ok rows")
    return df

def main():
    load_local_verify()
    workers=min(8,os.cpu_count()-1 or 4)
    ALL=list(SIG)
    PQ=["ML-DSA-44","ML-DSA-65","ML-DSA-87","Falcon-padded-512",
        "SLH-DSA-128s","SLH-DSA-128f","SLH-DSA-192f","SLH-DSA-256f"]
    REP=["Ed25519","ML-DSA-44","SLH-DSA-128f"]
    seeds=list(range(1,21))

    # E1 overhead (no loss, single seed), chain + fec
    cfgs=[]
    for s in ALL:
        cfgs.append(base(s,1,"chain","E1",loss=0.0))
        cfgs.append(base(s,1,"fec","E1",loss=0.0,fecR=0.25))
    run_cfgs(cfgs,workers,"E1_overhead",
        ["sigSize","mode"],["rxBytes","medMs","p95Ms","cpuFrac"])

    # E2 group scale M sweep
    cfgs=[]
    for M in [10,50,100,200]:
        for mode,rho in (("chain",.25),("fec",.25)):
            cfgs.append(base("ML-DSA-44",1,mode,"E2",M=M,loss=.05,fecR=rho))
    run_cfgs(cfgs,workers,"E2_scale",
        ["M","mode"],["jointFrac","medMs","p95Ms","rxBytes"])

    # E3 independent loss grid, chain + fec .25/.5
    cfgs=[]
    for s in ALL:
        for p in [0,.02,.05,.1,.15,.2]:
            for sd in seeds:
                cfgs.append(base(s,sd,"chain","E3",loss=p))
                cfgs.append(base(s,sd,"fec","E3",loss=p,fecR=.25))
                cfgs.append(base(s,sd,"fec","E3",loss=p,fecR=.5))
    # dedupe the seed=1 chain duplicates
    seen=set(); uniq=[]
    for c in cfgs:
        k=(c["sigSize"],c["mode"],c["loss"],c["fecR"],c["seed"])
        if k not in seen: seen.add(k); uniq.append(c)
    run_cfgs(uniq,workers,"E3_loss",
        ["sigSize","mode","loss","fecR"],
        ["dataFrac","condFrac","jointFrac","medMs","p95Ms","cpuFrac"])

    # E8 block-size n sweep (M2 data completeness)
    cfgs=[]
    for s in REP:
        for n in [8,16,32,64,128]:
            for p in [.05,.1]:
                for sd in seeds:
                    cfgs.append(base(s,sd,"chain","E8",n=n,loss=p))
                    cfgs.append(base(s,sd,"fec","E8",n=n,loss=p,fecR=.5))
    run_cfgs(cfgs,workers,"E8_blocksize",
        ["sigSize","mode","n","loss"],
        ["dataFrac","condFrac","jointFrac","p95Ms"])

    # E4 rtt / rate grid
    cfgs=[]
    for s in ["ML-DSA-44"]:
        for rtt in [10,20,50,100,200]:
            for rate in ["1Mbps","10Mbps","100Mbps"]:
                for sd in seeds[:15]:
                    cfgs.append(base(s,sd,"chain","E4",rttMs=rtt,lastRate=rate))
                    cfgs.append(base(s,sd,"fec","E4",rttMs=rtt,lastRate=rate,fecR=.25))
    run_cfgs(cfgs,workers,"E4_rttrate",
        ["rttMs","rate","mode"],["medMs","p95Ms","jointFrac"])

    # E5 redundancy sweep at p=.1
    cfgs=[]
    for s in ["ML-DSA-44","ML-DSA-87","SLH-DSA-128f","SLH-DSA-128s"]:
        for rho in [0,.1,.25,.5,.75,1.0]:
            for sd in seeds:
                cfgs.append(base(s,sd,"fec","E5",fecR=rho,loss=.1))
    run_cfgs(cfgs,workers,"E5_redundancy",
        ["sigSize","fecR"],["condFrac","jointFrac","rxBytes","p95Ms"])

    # E7 burst: clustered vs interleaved
    cfgs=[]
    for s in REP:
        for bl in [2,5,10,20]:
            for sd in seeds:
                cfgs.append(base(s,sd,"chain","E7",burst=1,burstLen=bl,loss=.1))
                cfgs.append(base(s,sd,"fec","E7",burst=1,burstLen=bl,loss=.1,fecR=.5,ileave=0))
                cfgs.append(base(s,sd,"fec","E7",burst=1,burstLen=bl,loss=.1,fecR=.5,ileave=4))
                cfgs.append(base(s,sd,"fec","E7",burst=1,burstLen=bl,loss=.1,fecR=.5,ileave=8))
    run_cfgs(cfgs,workers,"E7_burst",
        ["sigSize","burstLen","mode","ileave"],
        ["condFrac","jointFrac","p95Ms"])

    # E10 chunk-C sensitivity
    cfgs=[]
    for s in ALL:
        for C in [1400,1350,1280]:
            for sd in seeds:
                cfgs.append(base(s,sd,"fec","E10",chunkC=C,loss=.1,fecR=.5))
    run_cfgs(cfgs,workers,"E10_chunkC",
        ["sigSize","chunkC"],["condFrac","jointFrac","rxBytes"])

    # E9 all-family baseline summary
    cfgs=[]
    for s in ALL:
        for sd in seeds:
            cfgs.append(base(s,sd,"chain","E9",loss=.05))
            cfgs.append(base(s,sd,"fec","E9",loss=.05,fecR=.5))
    for sd in seeds:
        cfgs.append(base("Ed25519",sd,"persig","E9",loss=.05))
    run_cfgs(cfgs,workers,"E9_baseline",
        ["sigSize","mode","fecR"],
        ["jointFrac","medMs","p95Ms","cpuFrac","rxBytes"])
    print("ALL MATRIX EXPERIMENTS DONE")

if __name__=="__main__":
    main()

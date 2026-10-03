#!/usr/bin/env python3
"""rebuild_ci.py - regenerate agg and _ci CSVs from existing _raw CSVs.

No simulation is rerun. Fixes the count/group-key naming collision (the
replicate count is stored as 'reps', never overwriting a grouping key 'n').
"""
import math
import pandas as pd

OUT = "/mnt/e/pqc+zhengshu/pq-net-research/results/local/ns3"

SPEC = {
    "E1_overhead":  (["sigSize", "mode"], ["rxBytes", "medMs", "p95Ms", "cpuFrac"]),
    "E2_scale":     (["M", "mode"], ["jointFrac", "medMs", "p95Ms", "rxBytes"]),
    "E3_loss":      (["sigSize", "mode", "loss", "fecR"],
                     ["dataFrac", "condFrac", "jointFrac", "medMs", "p95Ms", "cpuFrac"]),
    "E8_blocksize": (["sigSize", "mode", "n", "loss"],
                     ["dataFrac", "condFrac", "jointFrac", "p95Ms"]),
    "E4_rttrate":   (["rttMs", "rate", "mode"], ["medMs", "p95Ms", "jointFrac"]),
    "E5_redundancy":(["sigSize", "fecR"], ["condFrac", "jointFrac", "rxBytes", "p95Ms"]),
    "E7_burst":     (["sigSize", "burstLen", "mode", "ileave"],
                     ["condFrac", "jointFrac", "p95Ms"]),
    "E10_chunkC":   (["sigSize", "chunkC"], ["condFrac", "jointFrac", "rxBytes"]),
    "E9_baseline":  (["sigSize", "mode", "fecR"],
                     ["jointFrac", "medMs", "p95Ms", "cpuFrac", "rxBytes"]),
}

for name, (groupkeys, meankeys) in SPEC.items():
    raw = f"{OUT}/{name}_raw.csv"
    df = pd.read_csv(raw)
    agg = df.groupby(groupkeys)[meankeys].agg(["mean", "std", "count"]).reset_index()
    agg.to_csv(f"{OUT}/{name}.csv", index=False)
    recs = []
    for keys, g in df.groupby(groupkeys):
        keys = keys if isinstance(keys, tuple) else (keys,)
        for mk in meankeys:
            x = g[mk].values
            m = x.mean()
            h = (x.std(ddof=1) / math.sqrt(len(x)) * 1.96) if len(x) > 1 else 0
            rec = dict(zip(groupkeys, keys))
            rec.update(metric=mk, mean=m, halfci=h, reps=len(x))
            recs.append(rec)
    pd.DataFrame(recs).to_csv(f"{OUT}/{name}_ci.csv", index=False)
    print(f"rebuilt {name}: {df.shape[0]} rows, {len(recs)} ci rows")
print("REBUILD DONE")

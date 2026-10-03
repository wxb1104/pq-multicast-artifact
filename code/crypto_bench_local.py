#!/usr/bin/env python3
"""crypto_bench_local.py - local signature microbenchmark.

PQC schemes via the oqs Python bindings (bundled liboqs); Ed25519 via the
`cryptography` package. Reports median keygen/sign/verify over enough
iterations and records public-key and signature sizes.
"""
import os, time, statistics, platform
import pandas as pd

ROOT="/mnt/e/pqc+zhengshu/pq-net-research"
OUT=f"{ROOT}/results/local"
os.makedirs(OUT,exist_ok=True)
MSG=b"x"*64

def host():
    cpu="?"
    try:
        for line in open("/proc/cpuinfo"):
            if line.startswith("model name"):
                cpu=line.split(":",1)[1].strip(); break
    except Exception: pass
    return cpu, os.cpu_count(), platform.platform()

def med(fn, iters):
    for _ in range(min(5,iters)): fn()
    ts=[]
    for _ in range(iters):
        t0=time.perf_counter(); fn(); ts.append((time.perf_counter()-t0)*1e6)
    return statistics.median(ts), iters

def bench_oqs():
    import oqs
    enabled=set(oqs.get_enabled_sig_mechanisms())
    cands={
      "ML-DSA-44":["ML-DSA-44","Dilithium2"],
      "ML-DSA-65":["ML-DSA-65","Dilithium3"],
      "ML-DSA-87":["ML-DSA-87","Dilithium5"],
      "Falcon-512":["Falcon-512"],
      "Falcon-padded-512":["Falcon-padded-512"],
      "SLH-DSA-128s":["SLH_DSA_PURE_SHA2_128S"],
      "SLH-DSA-128f":["SLH_DSA_PURE_SHA2_128F"],
      "SLH-DSA-192f":["SLH_DSA_PURE_SHA2_192F"],
      "SLH-DSA-256f":["SLH_DSA_PURE_SHA2_256F"],
    }
    rows=[]
    for name,opts in cands.items():
        mech=next((m for m in opts if m in enabled),None)
        if mech is None:
            print("missing",name); continue
        slow = "SLH" in name
        it_sig = 30 if slow else 300
        it_kg  = 10 if "Falcon" in name else (20 if slow else 200)
        with oqs.Signature(mech) as s:
            kg_us,_=med(lambda: s.generate_keypair(), it_kg)
            pk=s.generate_keypair()
            sig_us,_=med(lambda: s.sign(MSG), it_sig)
            sig=s.sign(MSG)
        with oqs.Signature(mech) as v:
            vu,_=med(lambda: v.verify(MSG,sig,pk), it_sig)
            assert v.verify(MSG,sig,pk)
        rows.append(dict(scheme=name,mech=mech,pk_bytes=len(pk),
            sig_bytes=len(sig),keygen_us=kg_us,sign_us=sig_us,verify_us=vu))
    return rows

def bench_ed():
    from cryptography.hazmat.primitives.asymmetric import ed25519
    def kg():
        k=ed25519.Ed25519PrivateKey.generate(); return k
    k=kg()
    kg_us,_=med(kg,300)
    sig_us,_=med(lambda: k.sign(MSG),300)
    pub=k.public_key(); sig=k.sign(MSG)
    vu,_=med(lambda: pub.verify(sig,MSG),300)
    return [dict(scheme="Ed25519",mech="Ed25519",pk_bytes=32,sig_bytes=64,
        keygen_us=kg_us,sign_us=sig_us,verify_us=vu)]

def main():
    rows=bench_ed()+bench_oqs()
    cpu,nc,sysv=host()
    for r in rows: r.update(cpu=cpu,ncpu=nc,system=sysv,message_bytes=len(MSG))
    df=pd.DataFrame(rows)
    df.to_csv(f"{OUT}/crypto_bench_local.csv",index=False)
    show=df[["scheme","pk_bytes","sig_bytes","keygen_us","sign_us","verify_us"]]
    print(show.to_string(index=False))

if __name__=="__main__":
    main()

#!/usr/bin/env bash
# Reproduce all three layers. Run from the repository root.
set -e
PY=${PYTHON:-python3}

echo "[1/4] cryptographic microbenchmark"
"$PY" code/crypto_bench_local.py

echo "[2/4] Monte Carlo simulation with closed-form checks"
"$PY" code/chain_mc2.py

echo "[3/4] build the ns-3 simulator"
NS3FLAGS=$(pkg-config --cflags --libs libns3.41 2>/dev/null \
          || pkg-config --cflags --libs ns3)
g++ -std=c++17 code/pqmc2.cc -o pqmc2 $NS3FLAGS

echo "[4/4] run the full ns-3 matrix"
"$PY" code/run_matrix2.py

echo "All layers completed."

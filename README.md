# Artifact: Post-Quantum Source Authentication for Multicast

This repository contains the source code and the complete measurement data that
support the manuscript on deploying post-quantum signatures for multicast source
authentication using connected-chain amortization and MTU-aware erasure coding.

The artifact has three layers:

1. a real cryptographic microbenchmark built against liboqs;
2. a large-sample Monte Carlo simulation of connected chains and FEC, checked
   against closed-form expressions;
3. a packet-level ns-3 simulation of a multicast distribution tree.

## Repository layout

```
code/                     simulation and analysis source
  pqmc2.cc                ns-3 packet-level multicast simulator
  crypto_bench_local.py   liboqs / Ed25519 microbenchmark
  chain_mc2.py            Monte Carlo simulation with closed-form checks
  run_matrix2.py          ns-3 full experiment matrix driver
  rebuild_ci.py           rebuild summary/CI tables from raw runs
  figs_common.py          shared figure style and helpers
  make_fig1_v2.py         mechanism figure
  fig2_crypto.py ... fig8_sensitivity.py   experimental figures
data/
  crypto_bench_local.csv  cryptographic microbenchmark results
  mc_indep.csv            Monte Carlo, independent loss
  mc_burst.csv            Monte Carlo, Gilbert-Elliott burst loss
  ns3/                    packet-level results (one prefix per experiment)
    E*.csv                per-configuration means
    E*_ci.csv             mean, 95% CI half-width and repetitions (long format)
    E*_raw.csv            every individual simulation run
```

### Experiment index (ns-3)

| Prefix | Experiment |
|---|---|
| E1_overhead | Per-receiver authentication overhead vs group size |
| E2_scale | Group-size scalability |
| E3_loss | Authentication probability vs independent loss |
| E4_rttrate | RTT and last-mile rate |
| E5_redundancy | FEC redundancy threshold |
| E7_burst | Gilbert-Elliott burst loss and interleaving |
| E8_blocksize | Block size |
| E9_baseline | Connected-chain / FEC / per-packet baseline |
| E10_chunkC | MTU chunk-size conservatism |

## Software versions

- liboqs 0.16.0 (and liboqs-python 0.16.0)
- ns-3 3.41
- Python 3 with numpy, pandas, scipy, matplotlib, cryptography
- A C++17 toolchain (g++) and pkg-config

## Reproducing the results

```bash
# 1. cryptographic microbenchmark
python code/crypto_bench_local.py

# 2. Monte Carlo simulation with closed-form checks
python code/chain_mc2.py

# 3. build the ns-3 simulator (pkg-config must find ns-3)
g++ -std=c++17 code/pqmc2.cc -o pqmc2 $(pkg-config --cflags --libs libns3.41)

# 4. run the full ns-3 matrix
python code/run_matrix2.py
```

`code/reproduce.sh` runs these steps in order. Summary and CI tables can be
rebuilt from the raw runs without re-running simulations using
`python code/rebuild_ci.py`.

## License

Released under the MIT License. See [LICENSE](LICENSE).

# Preserved incomplete current-candidate captures

These three labels are immutable validation-history checkpoints.  None is a
complete post-implementation measurement set, none supplies headline
comparisons, and none may be combined with another label.  The identities
below name the exact source, test, probe, and fixed-input bytes measured at each
attempt.  The v3 identity includes the accepted AR-07 production correction.
The later AR-08 correction changes only the measurement runner and its harness
tests; it does not retroactively change the v3 identity or its raw records.

## `current-candidate`

Candidate content identity:
`689974d2373f57f9f33074f833be96ffae80db9a2ee09fb5050405f430945fa7`
(374 entries).

- Valid section: `startup` (46 successful workers and complete postflight).
- Stopping section: `build`.  The original two-pass verifier treated the first
  warm pass after a cold multiprocess Solid2 build as an unchanged pass.  All
  nine Solid2 samples legitimately completed their root SCAD settlement on
  that pass, so the newly strict no-churn gate stopped the run.  This exposed a
  harness boundary error and led to the finite cold/first-warm/third-pass
  correction.  The failed build JSON retains all raw samples and postflight.
- Unavailable: `batch`, `projects`, `empirical`, `algorithms`, and `memory` were
  not started.

## `current-candidate-v2`

Candidate content identity:
`59fad19d6560b7830372adc33e31b0765b5932f6ffc4c1b8ec80af281aa837bf`
(374 entries).

- Valid sections: `startup`, `build`, and `batch`, each with successful worker,
  structural, identity, and immutable-inventory postflight checks.  They remain
  diagnostic checkpoints only because the label did not complete.
- Stopping section: `projects`.  Fresh-copy settle-to-unchanged evidence found
  continuous byte-identical SCAD/currency mutation in all three Abacus and all
  three V8 runs; Metamaquina2 was clean.  A separate finite three-pass Abacus
  diagnostic repeated the same churn on both transitions, ruling out another
  settlement boundary.  The no-churn gate correctly stopped on the production
  defect subsequently recorded as AR-07.  The failed project JSON retains all
  nine raw runs, full artifact maps, original-catalogue before/after snapshots,
  and postflight.
- Unavailable: `empirical`, `algorithms`, and `memory` were not started.

## `current-candidate-v3`

Candidate content identity:
`b8b16185cb9e524c8cd119ff291c4a8d206fe4389794ef5293021909db39a4b0`
(375 entries).

- Valid sections: `startup`, `build`, `batch`, `projects`, and `empirical`,
  each with successful worker, structural, identity, and immutable-inventory
  postflight checks.  They remain diagnostic checkpoints only because the
  label did not complete.
- Stopping section: `algorithms`.  Each of its three workers failed before
  measurement with `ModuleNotFoundError: No module named 'bench'`.  The runner
  put only the framework root on the absolute worker subprocess's
  `PYTHONPATH`, omitting its verified disposable fixture CWD.  The failed JSON
  preserves all three worker failures and its completed postflight.
- Unavailable: `memory` was not started.

## No-cherry-pick policy

Only one future label that completes and independently verifies all seven
sections may supply the current-candidate comparison, human summary, or final
evidence inventory.  Valid sections from any checkpoint above must not be
substituted into that complete label.  In particular, startup timing from an
incomplete capture is retained honestly here but cannot become the final
startup headline.

## Immutable raw-record SHA-256 inventory

```text
87100889eabf10190309077e308776fec2e5f3a79dfb0e57c057df8842ddce4d  current-candidate-candidate-identity.json
53a14b2b79f5d6f10cb86b456efc8be5e58158048a48285013792c84e81a7700  current-candidate-startup.json
f357ac095683eb6129d5baf0f2fe8d3950272920694bfad95b7340327d6eba17  current-candidate-build.json
e2f9e7cb19c7b100e4ef884e2dc68b42a74c8e0d0a6e8b7edf7e48733673dbde  current-candidate-v2-candidate-identity.json
f829dac01f07d63d67a6d3cb822d76f5d79b47329fc79dd92f6f2269fba61aeb  current-candidate-v2-startup.json
aff13a93649a6ad841a6cdf4f2af6f5d4b2a94096b48fe59125d4d9ffcf3520f  current-candidate-v2-build.json
78a5fd9e0a17b6f76f3deaf095e75f22f735585dba68cc45f757f6f366b96209  current-candidate-v2-batch.json
94d1f12c06a0458c173eb6746e4d8d4a4bf7eb4b161bca391b25bf0a5a9bbc64  current-candidate-v2-projects.json
350b6037a71819763de766ae4d5e7487143546cc5356b9b451ce0fe022f3b9a8  current-candidate-v3-candidate-identity.json
025202a945a71bb8ae76c9d4637b312be2cf70dbe2a42bb88dc0d3c80fc21b62  current-candidate-v3-startup.json
3211cc572a4544804c5ad20bd114f4da41bc08694058b266a9c9c2b157e58eb6  current-candidate-v3-build.json
9882465d0bffc15d52655bbf830e7383a7b069c938bffc81a5befbf105dbbbcd  current-candidate-v3-batch.json
9cdfdfa9e99acdeffadcdc1a3d645f36cbb3a95f38625b9f09921860df718468  current-candidate-v3-projects.json
0c69d523a9040965f465ea3d03a2dd85334f5e3822c8e36ba88f4e8171f35ebf  current-candidate-v3-empirical.json
dcbe5bd2c277ae803215c28c19d0f836cdf22cefe6fa806e7f1794d1f17bc50d  current-candidate-v3-algorithms.json
```

# Performance remediation disposition

All seven audit findings are implemented and measured; the two policy/history
items are deliberately preserved. These changes address the audited mechanisms,
**not** a claim that every workload is optimally fast. Final independent review
is green, including the timestamp-only document proof and final written claims;
the decision is recorded in [adversarial-review.md](adversarial-review.md).

The sole final comparative capture is
[current-candidate-v4](current-candidate-v4.md), with raw records linked below:
**141 successful workers across seven sections**, measured candidate
`d3615253809628a7b9e988354f669da26a0a84ab2ac3855ac8b6cd4d20841250`
over 375 source/test/probe/fixed-input entries at planning commit
`2ca4b9f06835d1133b6ad00eceecdee6e29b714c`.
Its [identity](current-candidate-v4-candidate-identity.json) and
[evidence inventory](current-candidate-v4-evidence-inventory.json) are separate
to avoid a self-referential hash. Production and framework tests equal the
passing full-v4 candidate; only the independently corrected harness runner and
its tests changed afterward. See [combined validation](validation.md).

## Finding-by-finding outcome

| Item | Implemented boundary and code | Red / green proof | Final empirical evidence and remaining limit | Disposition |
| --- | --- | --- | --- | --- |
| P01 — process-per-artifact overhead | One fresh spawned worker retains one sealed source generation, loaded root and assembled tree: [manager/build.py](../../../solid_node/manager/build.py), [core/builder.py](../../../solid_node/core/builder.py), [source_generation.py](../../../solid_node/source_generation.py). | [WP1](wp1.md), [WP2](wp2.md): stale-bytecode/load/source races, retained continuation, lock/reload outcomes, 25-child red and complete legacy/candidate 24-artifact map comparison. | [Build](current-candidate-v4-build.json): cold Solid2 24-artifact fixture uses one child, formerly 25. [Batch](current-candidate-v4-batch.json) and [projects](current-candidate-v4-projects.json) preserve observed output contracts. Source change/failure still requires a fresh interpreter; there is no persistent worker. | Remediated. |
| P02 — repeated publication mesh facts | Private versioned facts validated by one strong artifact observation and pinned bytes: [_artifact.py](../../../solid_node/_artifact.py), [core/pieces.py](../../../solid_node/core/pieces.py), [core/export.py](../../../solid_node/core/export.py), [viewers/browser.py](../../../solid_node/viewers/browser.py). | [WP3](wp3.md), [AR-02](ar02.md): two-process decode red, same-size/restored-mtime replacement, coherent copies, metadata freshness, malformed records, truncated-id collision and lower-cache identity. | [Empirical](current-candidate-v4-empirical.json): fresh Abacus/V8/Metamaquina2 publication reuses 5/24/100 fact records with zero piece mesh decodes/full hashes/payload reads. Tree metadata remains live. Retry is limited to three identity-change attempts; facts are not whole-document caching. | Remediated. |
| P03 — repeated SCAD/source work | Request-local census, current rigid path identity, compare-before-replace and assembly-phase final non-rigid SCAD publication: [source_generation.py](../../../solid_node/source_generation.py), [currency.py](../../../solid_node/currency.py), [node/base.py](../../../solid_node/node/base.py). | [WP4](wp4.md), [AR-07](ar07.md): retained red churn, re-ratified last-occurrence boundary, A/B/A, distinct in-memory compositions, pre/post-flush source races, partial atomic failure, flexible/direct immediate publication. | [Projects](current-candidate-v4-projects.json) and [empirical](current-candidate-v4-empirical.json): settled unchanged builds have zero SCAD/currency inode/mtime/ctime churn; each phase shares distinct-source observations. Calls to comparison helpers are not physical writes. Census is not persistent; pending SCAD retains one final text payload per distinct non-rigid path within a phase, not a universal byte cap. | Remediated, including re-ratified AR-07. |
| P04 — flexible binding cache churn | Full source/structure/binding/spec identity and access-ordered faceted geometry reuse: [test.py](../../../solid_node/test.py), [node/flexible.py](../../../solid_node/node/flexible.py). | [WP5](wp5.md), [AR-02/04](ar02.md): interleaving red, full-key/collision/eviction/override tests and stale nominal STL cannot enable flexible verdict caching. | [Empirical](current-candidate-v4-empirical.json): 80 V8 reads over three useful bindings construct three faceted geometries, formerly 35; high-water three, internal limit 64. Every flexible comparison still executes its selected Boolean; exact per-instance last-binding memo stays separate. | Remediated. |
| P05 — orientation cliff | Least-pressure-axis discovery, inclusive conservative overlap, legacy-X order, bounded fallback: [test.py](../../../solid_node/test.py). | [WP6](wp6.md): 128–1,024-box structural red, exhaustive/randomized/touching/rotation/permutation/order and dense fallback tests. | [Algorithms](current-candidate-v4-algorithms.json): 1,024 Y/Z-separated boxes need zero full-AABB checks instead of 523,776. [Real bounds](current-candidate-v4-empirical.json): 56/119/443 bounds yield 144/450/965 candidates with exact legacy set/order. Buffer limit 8,192 falls back to streaming X; true dense overlap can still require quadratic comparisons. | Remediated. |
| P06 — child naming cost | One parent-attribute ownership index and sibling-link snapshot per traversal in [node/base.py](../../../solid_node/node/base.py), [node/assembly.py](../../../solid_node/node/assembly.py), [node/internal.py](../../../solid_node/node/internal.py), [node/qualified.py](../../../solid_node/node/qualified.py), [core/serializer.py](../../../solid_node/core/serializer.py). | [WP7](wp7.md): wide-list red, direct/list alias precedence, explicit names, parent reassignment, mutable reorder and inter-child timing in all four consumers. | [Algorithms](current-candidate-v4-algorithms.json): 20 ticks use 20 index calls and zero single-child scans through 2,048 children, preserving names/history. Mutations during child recursion appear on the next traversal, as explicitly ratified. | Remediated. |
| P07 — exact placement retention | Exact-module-owned 512-entry LRU and managed-run reset: [exact.py](../../../solid_node/exact.py), [manager/test.py](../../../solid_node/manager/test.py). | [WP8](wp8.md), [exact fixture correction](exact-test-isolation.md): unbounded red, exact matrix-byte keys, hits/eviction, held evicted object, rebuilt source, unstable shape and Boolean equivalence. | [Memory](current-candidate-v4-memory.json): every 1,000/4,000/8,000-placement sample retains 512 entries; 12 repeated-working-set requests construct three and hit nine. Explicitly GC-qualified RSS is recorded, not a universal shape-byte or native allocator bound. | Remediated. |
| Dense statics | Deterministic old-order coefficient accumulation and sparse-equivalent global LP: [test.py](../../../solid_node/test.py). | [WP9](wp9.md): dense-reference/structural allocation red, existing and generated feasible/infeasible/near-tolerance equivalence, identical ordered diagnostics. | [Algorithms](current-candidate-v4-algorithms.json) and [memory](current-candidate-v4-memory.json): 1,000 free bodies use 13,000 nonzeros, 180,004 CSR bytes and 152,000 vector bytes; construction peak about 2.01 MB. Historical dense coefficients/slack identities imply 48/576 MB, calculated rather than allocated. HiGHS workspace is excluded; solver/mathematics/tolerances unchanged. | Remediated. |
| Exact/faceted precision choice | Explicit run policy remains in [test.py](../../../solid_node/test.py) and [manager/test.py](../../../solid_node/manager/test.py). | Existing kernel-policy tests and package suites in [validation](validation.md); [WP5](wp5.md)/[WP8](wp8.md) preserve routing. | [Empirical](current-candidate-v4-empirical.json) separately names exact and faceted V8 results at four instants. Exact remains default; volume epsilon belongs only to explicit faceted policy. Faster faceted observations are not substituted for exact answers or proof that kernels always agree. | Deliberately preserved; no silent precision tradeoff. |
| `Sim.trajectory` retention | Requested simulation history in [simulation/sim.py](../../../solid_node/simulation/sim.py) is unchanged. | Existing [simulation contract tests](../../../tests/test_simulation_sim.py) and final memory preservation gate. | [Memory](current-candidate-v4-memory.json): 4,000 ticks retain 4,000 trajectory entries and 4,000 one-driver values in each run. History remains proportional to requested ticks × drivers; no cap/eviction was introduced. | Deliberately retained; not a cache leak. |

## Evidence boundaries

- [Planning baseline](planning-head-baseline.md) is immutable and attributed
  to its actual original planning HEAD `4bcf4cb5`, not retroactively relabelled
  as the amended planning commit. The original audit and all 18 historical
  assets also remain byte-identical.
- The baseline retained STL count/bytes and manifest digest, **not complete
  filename-to-SHA-256 maps**. New maps prove current cold/warm/batch
  self-equivalence. Abacus/V8 available baseline fields compare equal;
  Metamaquina2's aggregate STL/piece fields match but its viewer manifest
  digest differs solely in 226 serialized node `mtime` values after a same-byte
  source timestamp refresh. Substituting only the old timestamps into the
  current document reproduces the exact saved baseline SHA-256 and length
  (173,799 bytes), versus the current 173,857 bytes. Literal baseline document
  equality is not claimed; all non-timestamp content is exactly accounted for.
  A full baseline-to-current map
  claim is not possible from the saved baseline evidence. WP2's
  separate controlled legacy/candidate fixture map proof is narrower.
- All catalogue builds use fresh disposable copies with recorded input
  hashes. Original commits, pre-existing dirty files, and selected source-byte
  hashes match the planning-baseline snapshots before/after. Those snapshots
  do not include source timestamps: Metamaquina2's metadata changed between
  captures while bytes/status/HEAD remained equal. Diagnostic reproduction
  and timestamp substitution are confined to disposable data/in-memory JSON;
  this task does not build or restamp an original project.
- [Incomplete captures](failed-captures.md) and the separately labelled
  `ar08-smoke` remain diagnostic history. Their favourable samples are not
  substituted into v4. The v4 comparison reports regressed timings as well as
  improvements; shared-host elapsed time/RSS is observational.
- Strong observation means real path/device/inode/size/mtime_ns/ctime_ns,
  within the ratified observable-filesystem boundary. A privileged external
  operation preserving every exposed identity field must explicitly
  invalidate artifacts; no metadata cache can detect that invisible change.
- The final correctness checkpoint has 1,773 passing tests, 353 subtests and
  16 explicitly recorded skips. Missing Sphinx, two absent vendor STEP
  fixtures, opt-in web capture and absent real JSCAD CLI coverage remain
  limitations, not green integration claims. Final post-archive validation
  is green at the same 1,773 tests and 353 subtests; logs, archive and lifecycle
  checks are recorded separately in [validation](validation.md).

# WP4 — Generation-local SCAD and write deduplication (P03)

## Scope and identity

WP4 adds no persistent snapshot or public cache.  Each WP1
`SourceGeneration` owns a set of completed base-SCAD identities and discards it
with the worker generation.  The key is the canonical artifact path plus the
full tuple `(mtime_ns, node-scoped source digest, source fingerprint)`.  A
missing digest or fingerprint is never shareable.  Metadata-only source change
therefore misses even when scoped content is equal, and a real edit hidden
beneath an unchanged aggregate maximum misses through its digest/fingerprint.

Only rigid base SCAD is eligible.  `render()` and `as_scad()` still run on
every previously unassembled node, preserving existing user-code behavior;
the completed base `scad_render`/publication is the reused work.  Operations
remain instance-local and distinct placements render differently in parent
documents.  Flexible and legacy binding-dependent non-rigid nodes bypass the
cache: the focused test uses an actual `FlexibleNode` subclass whose three
bindings emit three different snapshot imports at one SCAD path and proves all
three reach publication.  This avoids inventing a new binding/spec identity or
widening the ratified boundary.  Existing shortened structural artifact-id
collision behavior is not redesigned here.

That paragraph records the original WP4 checkpoint. AR-07 later proved that
leaving every non-rigid publication immediate caused continuous identical-byte
churn in repeated real Abacus and V8 assemblies. The pilot re-ratified a narrow
amendment: rigid generation still uses only current path identity, flexible and
direct/non-assembly generation stay immediate, and non-rigid/non-flexible SCAD
inside the assembly source phase is now coalesced to the immutable historical
last desired value per canonical path. See [ar07.md](ar07.md) for the red-first
correction, failure/source-race proof, finite disposable-project confirmation,
and memory/lifetime boundary. This amendment supersedes only the earlier
non-rigid immediate-bypass description; the historical commands, counts, and
hashes below remain provenance for the pre-AR-07 WP4 checkpoint.

Overlapping fingerprint, scoped-digest, timestamp, and file-digest work flows
through WP1's phase census.  The audit-scale structural cases exercise 59
repeated rigid instances and 191 overlapping closures over 210 distinct source
paths: user render runs 59 times and placements stay distinct, base SCAD is
generated once, and each distinct source payload is hashed once in the census.
The original project and historical P03 evidence were not modified; final
real-project measurement belongs to WP10.

## Compare before replace

SCAD text comparison reads the existing artifact through the coherent
`ArtifactSnapshot` seam before deciding to retain it.  The outcomes are:

- identical bytes, exact nanosecond stamp, and identical currency record:
  neither SCAD nor sidecar is replaced or restamped, preserving inode, mtime,
  and ctime;
- identical SCAD bytes with moved source metadata: retain the SCAD inode,
  refresh only its required stamp, and atomically replace the changed source
  record;
- changed SCAD bytes: write/stamp a private temporary and use the established
  drop-artifact-record / atomic artifact replacement / atomic new-record
  ordering.

`currency.record()` constructs deterministic desired bytes and coherently
compares the current sidecar.  It returns without mutation on equality.  Once
a difference is known it retains the conservative old behavior of dropping
the prior claim before atomic replacement, so interruption leaves no record
rather than a stale one.  A `None` digest still drops any record.  General
binary STL/BREP/flexible/imported publication remains on `currency.publish()`;
WP4 does not apply text suppression to those producer flows.

## Red and green proof

[wp4-red.log](wp4-red.log) records the initial three concrete failures: two
repeated instances performed two base SCAD generations; an identical build
replaced both files; and metadata-only change replaced SCAD instead of only
restamping it and refreshing the record.  It also records the review-driven
flexible-boundary red, where an initial broad eligibility rule wrongly reused
the second binding.

[wp4-green.log](wp4-green.log) records:

- **10 passed in 1.24 s** for focused identity, audit-scale, placement,
  flexibility, and exact-write behavior;
- **327 passed in 34.66 s** across F04/F05 currency, source/census, SCAD, STL,
  exact, sheet, flexible/Molejo, OpenSCAD/JSCAD, build-lock, and atomic
  publication coverage; and
- **100 passed plus 10 subtests in 52.19 s** for the post-review combined
  source-generation, retained-builder, reload recovery, lifecycle, lock,
  subprocess, and WP4 seams.

The restored-mtime and non-maximum contributor cases are real filesystem tests
in the F05/content-currency and WP1 generation suites, not mocked cache-key
claims.  The pre/post source race remains guarded by WP1's fresh phase
boundaries and pre-publication checkpoint; suppression occurs inside those
same phases and adds no broader snapshot boundary.

## Provenance and limits

- Planning source: `4bcf4cb5201d9d4bf25e16f1f950c3c667d6ec3c` on branch
  `performance-analysis`.
- Interpreter: `/home/asa/devel/libresolid-studio/.venv/bin/python`, invoked
  from this framework worktree with `PYTHONPATH="$PWD"` and `-B`.
- Candidate SHA-256 after the green runs:
  - `solid_node/source_generation.py`:
    `162a9d0e9f02945178f9f744acfe87ab27182c25a661247303cc1b0210fd96aa`
  - `solid_node/currency.py`:
    `32c7312211f680743c50df87168f66988398002456513b625a0b23907613e3bf`
  - `tests/test_generation_dedup.py`:
    `a8975f88a2e06aa2907317822f2ad8308cbc893069221e312c18100c47434704`
- `solid_node/node/base.py` is shared with WP1, WP3, WP5, and WP7; WP4 edits
  only `_atomic_write_text`, the source-generation import, and
  `generate_scad()`, so its whole-file hash is intentionally not presented as
  a WP4-only identity.
- A real JSCAD CLI is absent, as already recorded by WP1; deterministic adapter
  tests cover that boundary.  WP4 adds no external dependency or viewer work.
- No original project, historical baseline asset, task checkbox, progress
  record, baseline spec, ADR, OpenSpec lifecycle record, or catalogue entry was
  edited.  No commit or staging operation was performed.

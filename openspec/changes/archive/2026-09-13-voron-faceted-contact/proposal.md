## Why

The Voron 2.4r2 simulation cannot complete its frame integrity loop: two
unchanged source extrusions fail `assertNoSolidInterference` with a faceted
intersection volume of −9.947598300641403e−14 mm³, while the exact check passes.
The assembly assertion promises positive-volume interference, but currently
rejects every non-empty, nonzero result, including this negative measurement.

## What Changes

- Make a finite negative volume from a faceted candidate non-interfering for
  the whole-assembly integrity assertion, without adding a tolerance or
  altering the reported geometry.
- Preserve every positive-volume failure at zero run epsilon, including the
  smallest representable positive volume, and preserve non-finite failures.
- Keep the exact candidate path and the stricter pairwise/fit assertions
  unchanged. In particular, `assertNotIntersecting` continues to reject
  engine-reported non-empty faceted contact: it asks a different question.
- Add signed-result regression coverage and validate the unchanged Voron
  corner through the real CLI. Record the originating findings and the
  correction to the project's initial interpretation of the pairwise test.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `test-framework`: explicitly distinguish a finite negative faceted result
  from positive shared volume in whole-assembly interference checks; retain
  strict engine-emptiness semantics elsewhere.

## Impact

The implementation is confined to the assembly assertion in `solid_node/test.py`
and focused framework tests, with the accepted behavioral record updated at
closeout. No new dependency, public argument, source repair, cache-policy
change, viewer change, or broad-phase shortcut is proposed.

Origin: `projects/3D-Printers/Voron-2`, project commit `235451b`,
`simulation/tools/corner_probe.py:SourceCorner`, source solids 1262 and 1388.
The project's actual fastener overlaps still need a project-owned measured
inventory; this fix does not certify the frame or complete the printer.

Standalone framework cycle `voron-faceted-contact`, based on clean `main`
commit `b768bdf979552751d016dd89c2f5814693134f9a`. The pilot ratified this
scope and authorized implementation, fast-forward integration into unchanged
clean `main`, and resuming Voron on 2026-09-13: "ratify, go on".

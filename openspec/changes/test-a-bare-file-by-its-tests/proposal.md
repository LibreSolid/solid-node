## Why

`solid test path/to/file.py` on a file that defines several node classes
builds every one of them. A file that defines a machine and the
sub-assemblies it is made of — openvmp's `robot.py` defines `Foot`, `Leg`,
`Camera`, `Hip`, `Side` and `Don1` — cannot be tested by its bare path: a
sub-assembly whose ports are bound by its parent crashes when built
standalone, and the run dies before the machine's own contracts are
reached. The project's README tells the reader to name the class. Yet the
companion test file already says which classes it tests: every test case
beside a multi-class file must declare `node = <Class>`, or the run refuses
it. The run builds classes nobody asked about.

## What Changes

- A bare file reference covers the node classes its companion test cases
  declare, each once, in the file's definition order. A class no test case
  declares is not built.
- When the companion declares nothing — there is no companion file, or the
  file defines one class and its cases leave `node` implicit — the run
  covers every node class in the file, as today.
- A test case beside a multi-class file that does not declare its node
  still fails the run naming the case and the candidates; it now does so
  before any node is built.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `test-framework`: the "Test runner lifecycle" requirement's file-reference
  coverage — the classes the companion declares, not every class.

## Impact

- `solid_node/manager/test.py`, the file-reference branch of `handle`.
- `tests/test_manager_test.py`: one fixture with a parent and a sub-assembly
  that cannot build alone, one with no companion.
- Originating project: openvmp runs `solid test simulation/don1/robot.py`
  once this integrates; its README stops telling the reader to name the
  class. Project work, recorded in the shop's `docs/warts.md` plan.

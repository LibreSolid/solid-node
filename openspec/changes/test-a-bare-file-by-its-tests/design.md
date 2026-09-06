## Context

`TestCommand.handle` resolves a reference through `resolve_node`; a bare
file defining several node classes raises `AmbiguousNodeError`, and the
runner answers by selecting every class the file defines. Each selection is
built, then the companion's test cases are filtered to those declaring that
class. The declaration is mandatory beside a multi-class file, so the
companion already names exactly the classes under test; the runner reads it
one selection too late.

## Goals / Non-Goals

**Goals:**

- A bare file is testable when its companion says what to test.
- No change for a single-class file, a `file.py:Class` reference, a
  declared model name, or `--all`.

**Non-Goals:**

- Inferring which classes are "roots" from the node tree. The companion is
  the declaration; the runner does not guess.
- Building undeclared classes anyway "to check they build". A class worth
  building alone is worth a test case declaring it.

## Decisions

**Read the companion first.** In the ambiguous branch, load the companion's
test cases before selecting anything. Refuse an undeclared case there,
naming it and the candidates, with the message the loop used to produce.
Select the candidates the cases declare, in the file's definition order;
when none is declared, select every candidate as before.

**Keep the per-selection loop as it is.** It still re-reads the companion
and binds each case to the selection declaring it; the change is only which
selections exist.

## Risks / Trade-offs

- [A class that used to be built for free by a bare-file run is no longer
  built when no test declares it] → that build was never tested; a
  companion declaring the class restores it, and `solid build file.py:Class`
  builds it alone.

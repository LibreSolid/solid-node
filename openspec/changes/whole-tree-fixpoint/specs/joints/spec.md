## ADDED Requirements

### Requirement: An author-bound joint is cleared with its motion

A joint's coordinate holds a value and the joint's placement holds
operations, and the two are halves of ONE binding. The system SHALL drop
them together: at the start of an assembly's simulate phase, in the same
moment as the sweep that removes the operations that assembly applied,
the framework SHALL clear the value and the binder record of every
coordinate that assembly bound DURING ITS PREVIOUS SIMULATE PHASE —
including a coordinate the author's own `simulate()` bound.

A coordinate SHALL therefore never go on holding a value whose motion
has been swept. An assembly that binds a joint under a guard such as
`if <coordinate>.value is None:` SHALL find the coordinate unbound on
every run and SHALL rebind and re-place the body on every run, so the
pose it states on the first enumeration is the pose it states on the
second and the tenth.

A binding made OUTSIDE any simulate phase — in `__init__`, in a test, or
through a `render()` no walker drove — SHALL NOT be cleared, exactly as
an operation applied outside a phase is never swept, and two assemblies
that bind coordinates of one node SHALL clear only their own.

Between one enumeration and the next, a joint's coordinate SHALL go on
reading what the last enumeration bound, so a test, a serializer or a
pose capture that reads a joint after a walk reads the pose that walk
produced.

#### Scenario: A rest-default joint stands where it says it stands

- **WHEN** a root whose `simulate()` reads a child's prismatic
  coordinate, finds it unbound and binds it to a non-zero rest default
  is enumerated three times
- **THEN** the child carries the translation of that default on every
  run, and the coordinate reads that default after each of them

#### Scenario: A stale value cannot outlive its motion

- **WHEN** the same tree is enumerated a second time
- **THEN** at no point does the coordinate hold a value while the body
  carries no operation from it: the value and the operations were
  dropped together and rebound together

#### Scenario: A joint bound outside a phase keeps its value

- **WHEN** a test binds a joint of a node it constructed itself, with no
  walker and no simulate phase running, and then reads it
- **THEN** the value and the placement are still there, because nothing
  recorded the binding on a phase and nothing swept it

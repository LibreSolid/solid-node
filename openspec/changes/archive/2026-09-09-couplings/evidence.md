# Evidence (task 6.2)

The fixture train is `tests/coupling_project/`: three arbors meshed in a
row, the relations written POWER-first, `simulate()` binding only
`escape.turn`, and `mesh(driver, driven)` reading the tooth counts and
the registration off the two realized arbors.

    power  = Arbor(index=0, wheel_teeth=60, pinion_teeth=8)
    centre = Arbor(index=1, wheel_teeth=48, pinion_teeth=8, registration=3.0)
    escape = Arbor(index=2, wheel_teeth=30, pinion_teeth=6, registration=5.0)

    power.drives(centre, law=mesh)
    centre.drives(escape, law=mesh)

## The angles the backwards solve produces

`set_state(escape_angle=24.0)`, with both relations solved BACKWARDS
through the inverse of the law the fixture wrote:

| arbor | value | by |
|---|---|---|
| `escape.turn` | `24.0` | the author's `simulate()` |
| `centre.turn` | `-2.375` | `(24.0 - 5.0) / -8.0` |
| `power.turn` | `0.7166666666666667` | `(-2.375 - 3.0) / -7.5` |

Each arbor's own wirings then carry its coordinate into the wheel and
the rod that turn with it, in the arbor's own phase, from the value the
train solved in its parent's.

## The published expressions for the symbolic build

Serialized with nothing bound (`symbolic_document` binding every driver
to its qualified token), the three arbors' rotations are:

    escape:  escape_angle
    centre:  ((escape_angle - 5.0) / -8.0)
    power:   ((((escape_angle - 5.0) / -8.0) - 3.0) / -7.5)

and `bind_document` interns the shared tail exactly once (ADR-080), so
the document publishes:

    bindings: _b0 = ((escape_angle - 5.0) / -8.0)
              _b1 = ((_b0 - 3.0) / -7.5)
    power's rotation: _b1

`tests/test_couplings.py` evaluates the published `power` expression
through `_eval_openscad_expr`, the helper the ADR-022 parity tests use,
and asserts it equals the number the same relation gives under
`set_state`.

## The three refusal messages, verbatim

`UnreachedCoordinate` — a named relation with neither end bound:

    'great' (a drives b): nothing bound either end. a (Pulley).turn and
    b (Pulley).turn are both unbound when nothing changes any more, so
    the relation has no side to be read from. Bind one of them in
    simulate(), or state a relation that reaches one.

`DoublyBound` — the author's `simulate()` and a relation:

    b (Pulley).turn would be bound by the relation a drives b and by the
    author's simulate(). A coordinate has exactly one binder in one
    enumeration of the tree, and the framework does not compare two
    values to decide whether two statements agree: they are ordinarily
    symbolic expressions. Drop one of them.

`NotInvertible` — a forward-only law needed backwards:

    a drives b: b (Pulley).turn is the bound end, so the relation has to
    be read backwards, and its law <forward-only law '<lambda>'> offers
    no inverse. Give the law an inverse(y), or bind a (Pulley).turn
    instead.

A node is named by its instance path when the walk that is running has
linked it, and by its name and class otherwise — the fallback cycle 2's
joint range error already uses. The solve runs inside the parent's own
render, before that walk links the children it just produced, so the
first refusal of a fresh tree ordinarily reads `b (Pulley)` rather than
a dotted path.

## Full suite

`PYTHONPATH=$PWD .venv/bin/python -m pytest tests -q` on the completed tree:
1928 passed, 16 skipped, 497 subtests passed in 257.91s (2026-09-09).

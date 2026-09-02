## Context

Change `declarative-node-api` (archived, commits `12bae05` and `05a76b2`,
not integrated) introduced `NodeMeta`, `in_class_body()`, `_evaluate` and
realization. Three project migrations ran against it on 2026-09-02 and are
the evidence for this change; `openspec/changes/declarative-node-api-fixes`
stacks on that branch so framework `main` receives both together.

The comprehension defect is a CPython 3.12 mechanism. PEP 709 inlines list,
set and dict comprehensions into the enclosing frame; in a class body the
loop variable becomes a *hidden* fast local. While a hidden local is live,
`frame.f_locals` returns a fresh `dict` merging the namespace and the hidden
locals, not the `_DeclaringNamespace` the body runs in. The probe from the
Metamaquina2 migration shows it: the same frame reports `_DeclaringNamespace`
before the comprehension and `dict` inside it. The project requires Python
3.12 or later; 3.13 (PEP 667) may return the mapping again, and nothing
here depends on which.

## Goals / Non-Goals

**Goals:**

- A comprehension in a node class body declares, never instantiates.
- A `Flag` flows to a declared child like a numeric token.
- A framework-called `check()` for cross-parameter guards on declarative
  classes, so a migrated class need not grow an `__init__` for them.
- The declaring page states where stationary placement goes today.

**Non-Goals:**

- A vector, text, table or choice kind (pilot: an architecture matter for
  the projects, handled later).
- `.value` or operators on `Flag`; a declarative constraint language.
- Renaming `render()`, `shape()` or `assemble()`, or a once-after-realization
  placement hook — deferred with that rename.
- Changing the three project branches.

## Decisions

### D1: The body is recognized by a marker the namespace carries, in either form

`_DeclaringNamespace.__init__` stores a private sentinel under a private
key; `in_class_body()` accepts a frame whose locals are a
`_DeclaringNamespace` **or** a plain `dict` holding that sentinel (compared
by identity); `NodeMeta.__new__` removes the key before `type.__new__`, so
no class ever carries it. The copy CPython hands back during an inlined
comprehension is a copy of the namespace and so holds the marker.

Alternatives: (a) a registry of live namespaces keyed by frame id — a body
that raises leaves a stale entry, and a later frame at the same address
would turn an instance into a declaration silently; (b) recognizing any
class-body frame by `__qualname__` in its locals — a `TestCase` body's
`node = Engine()` would become a declaration; (c) forbidding comprehensions
in a body — would make the existing docs' pitfall permanent and leaves the
silent failure for anyone who tries. A guard in `NodeMeta.__new__` against
a class attribute holding node *instances* was considered and left out:
with D1 the only way an instance reaches a class attribute is a module-level
construction, which is a legacy idiom this change does not judge.

### D2: `_evaluate` resolves any named declaration, `Flag` included

`_evaluate(operand, values)` resolves an `Expression` as today and,
additionally, a named `Flag` to `values[name]`, raising the same
`ParameterError` as a formula when the name is not this class's. An
unnamed inline `Flag(True)` inside a declaration is a constant, like an
inline `Length(2.0)`. The child's `Flag.resolve` then sees a `bool`.
`Flag` gains nothing else.

### D3: `check()`, called after resolution and before realization

`AbstractBaseNode.check(self)` is a no-op. On a declarative class,
`__init__` calls `self.check()` immediately after `_parameters` is
resolved — parameters read as plain values through their descriptors,
`self.name` is set, nothing else exists yet. An exception propagates
unchanged: a guard raises `ValueError` and the tests that expect
`ValueError` from a constructor keep passing. Nothing is realized for a
refused instance, so a bad root builds no subtree.

Name: `validate(self, rendered)` is the render-output hook on leaves,
fusions and flexible parts and cannot mean two things; `check` collides
with nothing in `solid_node`. Because `check` is now a base attribute the
shadow guard refuses a parameter of that name, which is right.

Scope: the framework calls it only on a declarative instance. A
non-declarative class assigns its attributes after `super().__init__()`
returns, so a call from the base constructor would see none of them; such
a class keeps its guards where it has them. Alternatives: a class-body
`Check(expr, message)` — comparisons are refused in the algebra by
ADR-062, and a constraint form is a larger design the pilot has not
asked for; calling `check()` after children realize — later, costlier,
and a guard over parameters needs no children.

### D4: The placement split is documented as a recommendation for now

The declaring page gains a section stating: a declarative class may define
`__init__(self, **kwargs)`, call `super().__init__(**kwargs)` — after which
its children are realized and its parameters read as values — and place
its stationary parts once there; `render()` is for what moves. Recommended
for now, and named as provisional: the pilot will revisit placement with
the deferred lifecycle rename. ADR-064's consequences say the same.

## Risks / Trade-offs

- [The marker key is visible as a name in the class body while it runs
  (`locals()`)] → private dunder-style key; removed before the class exists;
  no test or project reads `locals()` in a body.
- [A future CPython changes what `f_locals` returns in a body] → the
  comprehension test pins the behaviour either way, since both forms are
  accepted.
- [`check()` becomes a base attribute a project may already use for
  something else] → the shadow guard makes a *parameter* named `check`
  fail loudly; a project *method* named `check` on a declarative class
  would now be called at construction — none of the three migrated
  projects has one (grep), and the changelog names the hook.
- [Authors put geometry work in `__init__` again] → the docs restrict it
  to placement and say why it is provisional.

## Migration Plan

Additive. A class body with a comprehension over module values, a flag
passed to a child, or a `check()` method behaves as described; everything
else is unchanged. No re-keying: identity is untouched.

## Open Questions

None for this change; the pilot's open items (kinds, placement hook,
lifecycle rename) are recorded as non-goals.

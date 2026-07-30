## Context

`Develop.handle()` selects its process set with one condition:

```python
if not args.openscad or args.web or args.web_dev or args.debug_web:
```

The web viewer therefore starts in every invocation except `--openscad`
passed alone. `--web` exists but is inert: it names the default. There is no
way to ask for the watch/rebuild loop by itself.

The build loop below that condition is already independent of the viewer. It
respawns a `Builder` subprocess per cycle, reacting to `BuildOutcome`, and the
only viewer coupling is the "restart WEB between cycles" block, which is
already guarded by `if web_proc and builder_proc`. `--callback` is likewise
handled entirely inside `Builder`, not by the viewer.

The originating caller is solid-node-shop, which runs
`solid develop root --callback URL` and renders the published `_build/`
directory through its own browser. It never opens the framework viewer, but
still pays `SOLID_NODE_PORT` for it.

## Goals / Non-Goals

**Goals:**

- Let a caller run the develop watch loop with no web viewer and no bound port.
- Keep `--callback` available in that mode; it is the reason the mode exists.
- Leave default behavior byte-for-byte unchanged.

**Non-Goals:**

- Changing `Builder`, `BuildSession`, publication, or callback semantics.
- Changing what the web viewer does when it does run (`web-viewer` capability
  is untouched).
- A machine-readable event stream on stdout. A caller that wants build
  *failures* still has only `_build/errors.json` — that is a separate concern
  and a separate change.
- Removing the inert `--web` flag.

## Decisions

**Decision: a `--no-web` flag rather than a `--headless` mode or an inverted
default.**

`--no-web` reads directly against the existing `--web` and states exactly what
it suppresses. Alternatives considered:

- `--headless` — ambiguous next to `solid snapshot`'s xvfb handling, where
  "headless" already means "no X display".
- Inverting the default so the viewer is opt-in — breaking, and wrong for the
  common interactive case.
- Reusing `--debug-builder` — it runs the builder once in-process without the
  watch loop, so it is not the same capability.

**Decision: conflicts are argument errors, not silent precedence.**

`--no-web` with `--web`, `--web-dev`, or `--debug-web` is a contradiction the
caller should see immediately, so it exits through `parser.error()` before any
process starts — the same treatment `--callback` already gets for
`--openscad`/`--web-dev`. `--no-web --openscad` is accepted because both
suppress the web viewer and agree about the outcome.

**Decision: the mode condition becomes explicit rather than more clever.**

Rather than extend the existing negated boolean chain, the viewer branch reads
as an explicit test of "did anyone ask to suppress the web viewer", which makes
the `--openscad`-alone rule and the `--no-web` rule visible side by side
instead of encoded in operator precedence.

**Decision: validation lives in `add_arguments`/`handle`, not argparse
mutual-exclusion groups.**

The existing `--callback` check is already a hand-written `parser.error()` in
`handle()`, because the rule is about combinations argparse cannot express as
one group. Keeping the new checks in the same place keeps one style.

## Risks / Trade-offs

- **A no-web session is silent about failures.** → Unchanged from today: a
  failed build writes `_build/errors.json` and the callback stays quiet. The
  no-web caller has no viewer to show the error banner, so it must read
  `errors.json` itself. Explicitly out of scope here and named as such.
- **Flag surface grows on a command that already has six.** → Accepted: the
  alternative is an inert `--web` and no way to get the loop alone.
- **`--no-web --openscad` is an accepted no-op combination.** → Accepted;
  rejecting agreeing flags would be noise.

## Migration Plan

None. Additive flag, default unchanged. Rollback is reverting the commit.

## Open Questions

None.

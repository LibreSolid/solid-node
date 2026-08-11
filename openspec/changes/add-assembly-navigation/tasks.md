## 1. Public API and tree state

- [ ] 1.1 Write red widget tests for serializable assembly metadata, inherited colours, path validation, focus, and visibility.
- [ ] 1.2 Add public assembly metadata and API-version-4 handle declarations without exposing renderer internals.
- [ ] 1.3 Extend WidgetTree path lookup and render filtering for focused and hidden subtrees.

## 2. Reconciliation and lifecycle

- [ ] 2.1 Write red targeted-update tests that retain valid focused/hidden paths and clear missing paths without refetching unchanged geometry.
- [ ] 2.2 Reapply assembly-navigation state across artifact and manifest updates while preserving existing failure containment.
- [ ] 2.3 Update package API version, generated/public declarations, compatibility tests, and the development viewer only where its API check requires it.

## 3. Verification

- [ ] 3.1 Run focused widget tests, type checking, package build, and the relevant framework test suite.
- [ ] 3.2 Exercise the originating Studio caller against the built API and record the result before completing the framework cycle.
- [ ] 3.3 Validate the framework OpenSpec change and assess whether the confirmed public-handle boundary warrants an ADR.

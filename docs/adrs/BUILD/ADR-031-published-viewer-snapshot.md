# ADR 031: Published viewer snapshot

**Status:** Accepted

**Date:** 2026-07-20

**Origin:** solid-node-shop Sprint 001 STORY-005

## Context

The ordinary build directory was atomically publishable but contained only
geometry files.  The development viewer obtained the corresponding tree,
operations, colours, and model addresses by importing project Python, which a
long-lived shop-floor process must not do.

## Decision

The builder writes `viewer.json` into its staging build directory after the
model is assembled and its STLs are current.  The snapshot records the same
recursive state served by NodeAPI, with model paths relative to the build
root.  It is published atomically with `_build`.  Private NodeAPI gains a
snapshot-backed constructor that serves that directory without source loading.

## Consequences

Callback consumers can treat a completed build publication as both geometry
and viewer state, and retain the prior viewer state when a later build fails.
The snapshot remains a private framework interface; hosts reuse NodeAPI rather
than parsing it themselves.

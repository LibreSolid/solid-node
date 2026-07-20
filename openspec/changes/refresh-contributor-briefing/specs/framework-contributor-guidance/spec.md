## ADDED Requirements

### Requirement: Framework-owned contributor briefing
The framework SHALL provide a contributor briefing that distinguishes durable
framework orientation and verification information from shop-owned development
workflow.

#### Scenario: Contributor needs framework orientation
- **WHEN** a contributor reads the framework contributor briefing
- **THEN** it identifies the relevant framework areas and points to the
  architecture synthesis, baseline specifications, and ADRs for detailed
  records.

#### Scenario: Contributor uses a shop-managed workflow
- **WHEN** the contributor briefing is read in a shop-managed framework change
- **THEN** it does not prescribe agent lifecycle, worktree, commit, or
  publication policy.

### Requirement: Framework verification guidance
The contributor briefing SHALL explain the role of direct pytest coverage and
the meta-project test harness without relying on a developer-specific path or
assistant identity.

#### Scenario: Framework behavior needs end-to-end proof
- **WHEN** a contributor changes behavior involving node loading, rendering,
  keyframes, meshes, or the `solid test` subprocess path
- **THEN** the briefing directs them to the meta-project harness and explains
  why paired valid and adversarial-invalid fixtures provide useful evidence.

#### Scenario: Contributor prepares local verification
- **WHEN** a contributor reads the briefing's runtime prerequisites
- **THEN** it names framework-relevant tools and environment controls without
  hard-coding a local checkout or virtualenv path.

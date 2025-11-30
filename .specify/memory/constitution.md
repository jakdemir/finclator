<!--
Sync Impact Report:
Version change: (none) → 1.0.0
Modified principles: N/A (initial constitution)
Added sections: Core Principles (2 principles), Governance
Removed sections: N/A
Templates requiring updates:
  ✅ .specify/templates/plan-template.md - Constitution Check section already generic
  ✅ .specify/templates/spec-template.md - No constitution-specific constraints
  ✅ .specify/templates/tasks-template.md - No constitution-specific task types
  ⚠ .cursor/commands/speckit.constitution.md - No updates needed (generic command)
Follow-up TODOs: None
-->

# Finclator Constitution

## Core Principles

### I. Simplicity & Focus

The MVP MUST be as light as possible, focusing only on the core prediction logic and data acquisition. Non-essential features (e.g., user accounts, complex UI/UX) are deferred. Do NOT over DOCUMENT! 

**Rationale**: Early delivery of core value requires eliminating all non-critical complexity. Features that do not directly contribute to prediction accuracy or data quality must be deferred until after MVP validation.

### II. Data-Driven Trust

The core value proposition is the formulated trust score. The methodology for calculating this score MUST be transparent, auditable, and directly linked to influencer sentiment and historical market performance. but don't over document!

**Rationale**: Trust in the prediction system depends on users understanding how scores are derived. The methodology must be verifiable and grounded in measurable data sources (influencer sentiment, historical market performance) to establish credibility.

## Governance

This constitution supersedes all other development practices and decisions. All feature specifications, implementation plans, and code reviews MUST verify compliance with these principles.


**Amendment Procedure**: Changes to this constitution require:
1. Documentation of the rationale for the change
2. Update to version number following semantic versioning (MAJOR.MINOR.PATCH)
3. Propagation of changes to dependent templates and documentation
4. Update of the Sync Impact Report at the top of this file

**Versioning Policy**:
- **MAJOR**: Backward incompatible governance/principle removals or redefinitions
- **MINOR**: New principle/section added or materially expanded guidance
- **PATCH**: Clarifications, wording, typo fixes, non-semantic refinements

**Compliance Review**: All PRs and feature specifications must include a Constitution Check that verifies alignment with these principles. Violations must be justified in the Complexity Tracking section of implementation plans.

**Version**: 1.1.0 | **Ratified**: 2025-11-30 | **Last Amended**: 2025-11-30

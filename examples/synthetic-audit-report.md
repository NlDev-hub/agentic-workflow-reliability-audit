# Synthetic Audit Report — Demo Agent Scheduler

This fictional example shows the style of an Agentic Workflow Reliability Audit. It uses synthetic examples only and no real customer, company, user, or product data.

## Workflow observed

A fictional scheduler checks a task queue every 15 minutes. It should act on ready items, ignore parked items, and produce an evidence bundle when it changes state.

## Findings

### Finding 1 — Ready item semantics are too broad

The scheduler marks generic research as `ready`, even when no buyer, maintainer, platform, or payment signal exists.

Suggested fix: require `ready` items to include a conversion target, evidence path, and exact next allowed action.

### Finding 2 — No anti-repeat gate

The same low-value route can be reselected after previous no-go evidence.

Suggested fix: add a failed-route ledger with `reopen_only_if` conditions.

### Finding 3 — Completion claims need evidence

The worker reports progress but does not always name verification commands or not-touched boundaries.

Suggested fix: require the evidence bundle template for non-trivial claims.

## Boundary

This is a practical workflow review example. It does not guarantee ROI, security, compliance, or automation success.

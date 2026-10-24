# Record transitions

Generated from validator transitions and schema enums. Regenerate with `python scripts/render_record_states.py`; CI checks for drift.

Commit gates as they occur. A valid runner receipt also permits a planned run to reach a terminal state in one Git commit because it records the actual start. Terminal manifests remain immutable.

## Question

```mermaid
stateDiagram-v2
    state "draft" as draft
    state "active" as active
    state "resolved" as resolved
    state "unresolved" as unresolved
    draft --> active
    draft --> unresolved
    active --> resolved
    active --> unresolved
    unresolved --> active
```

## Task

```mermaid
stateDiagram-v2
    state "ready" as ready
    state "running" as running
    state "blocked" as blocked
    state "reviewed" as reviewed
    state "cancelled" as cancelled
    ready --> blocked
    ready --> cancelled
    ready --> running
    running --> blocked
    running --> cancelled
    running --> reviewed
    blocked --> cancelled
    blocked --> ready
    blocked --> running
```

## Source

```mermaid
stateDiagram-v2
    state "unreviewed" as unreviewed
    state "source_checked" as source_checked
    state "disputed" as disputed
    state "superseded" as superseded
    unreviewed --> disputed
    unreviewed --> source_checked
    unreviewed --> superseded
    source_checked --> disputed
    source_checked --> superseded
    disputed --> source_checked
    disputed --> superseded
```

## Hypothesis

```mermaid
stateDiagram-v2
    state "proposed" as proposed
    state "under_test" as under_test
    state "supported_within_scope" as supported_within_scope
    state "contradicted" as contradicted
    state "unresolved" as unresolved
    state "superseded" as superseded
    proposed --> superseded
    proposed --> under_test
    proposed --> unresolved
    under_test --> contradicted
    under_test --> superseded
    under_test --> supported_within_scope
    under_test --> unresolved
    supported_within_scope --> superseded
    supported_within_scope --> under_test
    supported_within_scope --> unresolved
    contradicted --> superseded
    contradicted --> under_test
    unresolved --> superseded
    unresolved --> under_test
```

## Experiment

```mermaid
stateDiagram-v2
    state "draft" as draft
    state "protocol_reviewed" as protocol_reviewed
    state "implementation_reviewed" as implementation_reviewed
    state "executing" as executing
    state "completed" as completed
    state "superseded" as superseded
    draft --> protocol_reviewed
    draft --> superseded
    protocol_reviewed --> draft
    protocol_reviewed --> implementation_reviewed
    protocol_reviewed --> superseded
    implementation_reviewed --> draft
    implementation_reviewed --> executing
    implementation_reviewed --> superseded
    executing --> completed
    executing --> superseded
    completed --> superseded
```

## Run

```mermaid
stateDiagram-v2
    state "planned" as planned
    state "started" as started
    state "completed" as completed
    state "failed" as failed
    state "cancelled" as cancelled
    planned --> cancelled
    planned --> started
    started --> cancelled
    started --> completed
    started --> failed
    planned --> completed: verified runner receipt
    planned --> failed: verified runner receipt
```

## Observation

```mermaid
stateDiagram-v2
    state "unreviewed" as unreviewed
    state "reviewed" as reviewed
    state "disputed" as disputed
    state "superseded" as superseded
    unreviewed --> disputed
    unreviewed --> reviewed
    unreviewed --> superseded
    reviewed --> disputed
    reviewed --> superseded
    disputed --> reviewed
    disputed --> superseded
```

## Claim

```mermaid
stateDiagram-v2
    state "unreviewed" as unreviewed
    state "source_checked" as source_checked
    state "provisionally_supported" as provisionally_supported
    state "disputed" as disputed
    state "needs_review" as needs_review
    state "superseded" as superseded
    unreviewed --> disputed
    unreviewed --> provisionally_supported
    unreviewed --> source_checked
    unreviewed --> superseded
    source_checked --> disputed
    source_checked --> needs_review
    source_checked --> provisionally_supported
    source_checked --> superseded
    provisionally_supported --> disputed
    provisionally_supported --> needs_review
    provisionally_supported --> superseded
    disputed --> needs_review
    disputed --> superseded
    needs_review --> disputed
    needs_review --> provisionally_supported
    needs_review --> source_checked
    needs_review --> superseded
```

## Review

```mermaid
stateDiagram-v2
    state "draft" as draft
    state "completed" as completed
    state "superseded" as superseded
    draft --> completed
    draft --> superseded
    completed --> superseded
```

## Decision

```mermaid
stateDiagram-v2
    state "proposed" as proposed
    state "accepted" as accepted
    state "replaced" as replaced
    proposed --> accepted
    proposed --> replaced
    accepted --> replaced
```

## Project state

`research/state.yaml` is a pointer/status document rather than a lifecycle record. Its `phase` is free text; these links are type-checked.

```mermaid
flowchart LR
    State --> active_question["active_question: Q or null"]
    State --> active_tasks["active_tasks: TASK IDs"]
    State --> current_experiment["current_experiment: EXP or null"]
    State --> blockers["blockers and next_decision"]
```

# AGENT.md

## Product Definition

This project should be developed as a **paper knowledge-base analysis Agent**.

The intended product is not a generic academic chatbot and not a full thesis-writing system. Its purpose is to help users turn a project-level collection of papers into:

1. a traceable literature review
2. a traceable innovation-point report

The system should support academic QA, but QA is not the final product. QA is the analysis interface over a selected paper scope or knowledge graph scope.

## One-Sentence Product Description

Users upload or search papers, the system parses and stores them, builds paper cards, evidence tables, and a knowledge graph, then lets users ask questions over selected papers or graph subgraphs and generate literature reviews and innovation-point reports grounded in that selected evidence.

## Target User

Primary users:

- undergraduate thesis students
- master's students preparing literature reviews or thesis topics
- early-stage researchers exploring a research direction
- users who have collected papers but do not know how to summarize them or find viable innovation points

The user need is:

```text
I have a topic and a batch of papers.
What do these papers say?
How are they related?
What can I write as a literature review?
What innovation points are actually supported by evidence?
```

## Core Workflow

The product workflow must remain:

```text
1. Create research project
2. Upload/search/import papers
3. Parse and store papers
4. Generate paper cards
5. Extract evidence table
6. Build project knowledge graph
7. User selects a scope
8. User asks QA questions over that scope
9. User generates literature review or innovation-point report
10. System provides traceable evidence and versioned artifacts
```

## Core Concepts

### 1. Project Paper Library

Each research project owns a paper library.

The library should include:

- uploaded PDF files
- searched papers
- imported DOI / BibTeX / RIS records
- metadata
- parsed full text
- chunks
- embeddings
- paper cards
- evidence records
- knowledge graph nodes and edges

### 2. Paper Card

A paper card is the structured summary of one paper.

Recommended fields:

```text
title
authors
year
venue
abstract
research question
method
dataset / sample
key findings
limitations
future work
related topics
possible supported innovation points
```

### 3. Evidence Table

The evidence table is the structured basis for reviews and reports.

Recommended fields:

```text
paper_id
research_question
method
data_or_sample
finding
limitation
future_work
topic
evidence_strength
citation_context
```

Generation should prefer:

```text
paper cards + evidence table + KG relations
```

over:

```text
raw prompt + whole PDF text
```

### 4. Knowledge Graph

The graph should represent academic relationships, not just citations.

Recommended nodes:

```text
Paper
Author
Topic
Task
Method
Dataset
Finding
Limitation
Gap
InnovationPoint
```

Recommended relations:

```text
Paper -> BELONGS_TO_TOPIC -> Topic
Paper -> STUDIES_TASK -> Task
Paper -> USES_METHOD -> Method
Paper -> USES_DATASET -> Dataset
Paper -> REPORTS_FINDING -> Finding
Paper -> HAS_LIMITATION -> Limitation
Limitation -> SUGGESTS_GAP -> Gap
Gap -> SUPPORTS_INNOVATION -> InnovationPoint
Paper -> CITES -> Paper
```

### 5. Retrieval Scope

Scope-based QA is a core differentiator.

Users should be able to ask questions over a selected scope:

```text
all project papers
selected papers
a topic group
a method group
a year range
a graph node
a graph subgraph
an innovation-point evidence set
```

A retrieval scope may look like:

```json
{
  "project_id": "proj_001",
  "selected_paper_ids": ["p1", "p2", "p3"],
  "selected_topic_ids": ["topic_llm_feedback"],
  "selected_graph_node_ids": ["method_rag"],
  "include_neighbors": true,
  "graph_hops": 2,
  "time_range": ["2021", "2026"]
}
```

QA responses should state the scope:

```text
This answer is based only on the selected 8 papers and their 2-hop graph neighborhood.
```

## Formal Artifacts

The product has only two formal generated artifacts in the current scope.

### 1. Literature Review

Generated from:

```text
selected papers
paper cards
evidence table
topic clusters
knowledge graph relations
user research goal
```

Recommended structure:

```text
1. Research background
2. Topic clusters
3. Representative papers and research timeline
4. Main methods
5. Main findings
6. Limitations of existing work
7. Future trends
8. References and evidence trace
```

### 2. Innovation-Point Report

Generated from:

```text
knowledge graph gaps
shared limitations
method-task missing links
underused datasets
future work aggregation
evidence strength
user constraints
```

Each innovation point should include:

```text
name
description
why it is innovative
existing research foundation
research gap
supporting papers
limiting or contradictory evidence
feasibility
risk
possible thesis topic
```

Innovation points must not be generic phrases such as:

```text
combine deep learning
expand sample size
use multimodal data
improve model performance
```

unless the system can explain the exact paper evidence and graph gap behind them.

## When To Generate Reports

Reports should not be generated on every QA turn.

Valid triggers:

1. user explicitly clicks "Generate Literature Review"
2. user explicitly clicks "Generate Innovation Report"
3. user asks a generation instruction in QA
4. the paper library reaches a useful threshold and the system suggests generation
5. new papers are added and the system suggests incremental update
6. user saves a QA answer as report material

QA is for exploration and analysis. Reports are confirmed artifacts.

## QA Behavior

QA should support:

```text
scope-based answering
paper comparison
topic summary
method summary
limitation analysis
innovation-point explanation
evidence tracing
graph-neighborhood explanation
```

QA should not behave like a generic web chatbot.

Every substantial answer should include:

```text
answer
scope used
supporting evidence
uncertainty or limitations
optional next action
```

Possible next actions:

```text
add to literature review
add to innovation report
generate review from current scope
generate innovation report from current scope
expand scope to all project papers
show evidence graph
```

## Product Inspiration To Preserve

This product should inherit selectively from the research in `docs/research/论文Agent前沿开发报告.md`:

- GPT Researcher: planning, multi-source search, recursive research
- SciSage: reflection over review structure and evidence quality
- STORM / Co-STORM: multi-perspective knowledge synthesis
- PaperDebugger: traceability and user approval, but not editor-plugin scope
- Agent Harness: evaluator, checkpoint, audit trail, HITL, citation verification
- GraphRAG: graph-grounded QA and subgraph summarization

It should also learn from current research products:

- Elicit: evidence tables and systematic review workflow
- NotebookLM: sources + QA + generated artifacts
- Consensus: multi-paper conclusion aggregation
- Scite: supporting / contrasting / mentioning evidence
- ResearchRabbit / Litmaps / Connected Papers: paper graph exploration
- Rayyan / Covidence / DistillerSR / ASReview: screening and evidence extraction

## Explicit Non-Goals

Do not drift into these features in the current product phase:

```text
full paper generation
full thesis generation
paper polishing
AI detection avoidance
plagiarism reduction
formatting and typesetting
defense PPT generation
generic chat over the internet
all-in-one academic assistant dashboard
Overleaf / VS Code plugin
complex collaboration workflow
```

These may be separate future products, but they are not the current goal.

## MVP

The MVP should prove this loop:

```text
create project
  -> upload/search 20-30 papers
  -> parse papers
  -> generate paper cards
  -> extract evidence table
  -> build simple knowledge graph
  -> select papers/topic/subgraph
  -> ask scope-based QA
  -> generate literature review
  -> generate innovation-point report
  -> trace claims back to papers and graph relations
```

If a feature does not help this loop, defer it.

## Quality Requirements

Generated reviews and innovation reports should be checked for:

```text
citation correctness
evidence coverage
claim-to-paper traceability
scope clarity
generic innovation phrases
unsupported conclusions
contradictory evidence
method and data feasibility
```

## Final Guardrail

The product should always answer this promise:

> Turn a selected set of papers into a traceable research understanding, then produce a literature review and innovation-point report grounded in that evidence.

Do not optimize for writing more text. Optimize for better evidence-grounded academic analysis.


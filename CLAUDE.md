# CLAUDE.md

This repository is building a focused academic research analysis product.

## Product Direction

The product is:

> A paper knowledge-base analysis Agent that lets users upload/search papers, build a project-level paper library and knowledge graph, ask scope-based questions over selected papers or graph substructures, and generate two formal artifacts: a literature review and an innovation-point report.

The product is not a general full-paper writing platform.

## Non-Negotiable Scope

Keep the product centered on this workflow:

```text
Project paper library
  -> paper parsing and storage
  -> paper cards and evidence table
  -> knowledge graph
  -> selected-scope KG/RAG QA
  -> literature review
  -> innovation-point report
```

Do not expand the product into these areas unless explicitly requested:

- full thesis or full paper writing
- paragraph-by-paragraph paper revision
- polishing, rewriting, or AIGC reduction
- formatting, typesetting, or reference style tooling as a primary feature
- defense PPT generation
- Overleaf / VS Code plugins
- broad all-in-one student paper platform features

## Core Product Rules

1. **Paper library first**  
   Features should start from uploaded, searched, or imported papers. The system must store papers, parsed text, metadata, chunks, paper cards, evidence records, and graph nodes/edges.

2. **Evidence before generation**  
   Literature reviews and innovation reports should be generated from structured evidence, not directly from a title or prompt.

3. **Scope-based QA is central**  
   QA must support user-selected scopes: selected papers, topic groups, method groups, year ranges, or knowledge graph subgraphs.

4. **Only two formal artifacts**  
   Formal outputs are:
   - Literature Review
   - Innovation-Point Report

5. **Knowledge graph must be user-visible in value**  
   The graph should not be a hidden buzzword. It should drive QA, evidence tracing, innovation discovery, and scoped report generation.

6. **Traceability is mandatory**  
   Answers, review sections, and innovation points should cite the papers/evidence/graph relations that support them.

## Decision Test

Before adding or changing a feature, ask:

```text
Does this improve one of these?
1. paper ingestion/storage
2. paper card or evidence extraction
3. knowledge graph construction/retrieval
4. selected-scope QA
5. literature review generation
6. innovation-point report generation
7. evidence traceability and quality control
```

If the answer is no, the feature is probably outside the current product goal.

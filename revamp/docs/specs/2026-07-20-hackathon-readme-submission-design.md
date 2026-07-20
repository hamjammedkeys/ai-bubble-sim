# Hackathon README Submission Design

## Goal

Update the repository README so a general hackathon judge can quickly understand
what FragilityGraph does, run it locally, inspect its sample data, and see how
GPT-5.6 and Codex accelerated the implementation without overstating their role.

## Category

**Work and productivity.** FragilityGraph is an analyst workflow tool: it reduces
the time required to read long SEC filings, verify financial relationships, and
explore how a company shock may propagate through an infrastructure network.

## Narrative

Use a technical build story in the builder's voice:

1. Start with the filing-analysis problem and the product's evidence-first answer.
2. Show the main workflow from filing URL to reviewed graph to scenario run.
3. List only capabilities present in the repository.
4. Explain the included hero dataset and how to load or recreate it.
5. Preserve the existing local setup, deployment, verification, and troubleshooting instructions.
6. Add a concrete account of Codex collaboration and the engineering decisions retained by the builder.

## Codex and GPT-5.6 Story

The README will distinguish assistance from ownership. It will describe Codex as
an iterative engineering collaborator used for repository exploration, design,
implementation, test creation, browser-based debugging, and deployment hardening.
It will highlight these verifiable examples:

- replacing the filing character cutoff with chunked full-filing extraction;
- designing evidence review and scenario interaction flows;
- diagnosing graph hover and propagation rendering regressions with automated browser checks;
- adding Neon, Render, and Vercel deployment support;
- repeatedly running backend and frontend verification loops.

The README will state that product scope, UX trade-offs, category choice, and
acceptance of the final behavior remained human decisions. It will not claim that
AI autonomously created the project or that generated code was accepted without review.

## Structure

The revised README will contain:

- category and concise project description;
- problem and product workflow;
- current features and architecture;
- hero/sample data guidance;
- Codex/GPT-5.6 collaboration and key decisions;
- prerequisites, quick start, LLM configuration, deployment, verification, and troubleshooting;
- honest limitations, including evidence quality and non-predictive scenario outputs.

## Success Criteria

- A judge can identify the category, intended user, input, output, and differentiator in under one minute.
- Every feature claim maps to implementation present in `revamp`.
- A new contributor can run the app without external sample files in fallback mode.
- The AI collaboration section names specific tasks and human decisions.
- Existing setup and deployment commands remain accurate.

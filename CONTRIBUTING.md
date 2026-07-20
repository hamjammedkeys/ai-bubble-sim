# Contributing to FragilityGraph

Thanks for your interest in contributing! This guide covers how to set up your
environment, the standards we hold code to, and how to get a change merged.

## Code of conduct

Be respectful and constructive. Assume good faith, keep discussion focused on the
work, and help make this a welcoming project for everyone.

## Where the code lives

Active development happens in the [`revamp/`](revamp/) directory:

- [`revamp/backend`](revamp/backend) — FastAPI service (Python).
- [`revamp/frontend`](revamp/frontend) — Next.js app (TypeScript).

## The one non-negotiable: evidence over invention

FragilityGraph exists to be trustworthy where LLMs usually aren't. Any change you
propose **must preserve** these guarantees:

1. **No invented numbers.** A value in the graph must trace to a verbatim passage
   in a source document. If a filing doesn't disclose it, the answer is *unknown*.
2. **The model proposes, a human approves.** Extracted relationships enter as
   *candidates*. They must be reviewed and approved before any scenario uses them.
   Do not add auto-approve paths.
3. **Honest scenario outcomes.** Keep the impact / exposure / unresolved
   distinction intact. Exposure is an amount at risk, not a realized loss.

A PR that adds a feature by fabricating or auto-trusting figures will be declined
even if the code is otherwise excellent.

## Getting set up

Follow the [Getting started](README.md#getting-started) section of the README to
run the backend and frontend locally.

## Making a change

1. **Open an issue first** for anything non-trivial, so we can agree on the
   approach before you invest time.
2. **Fork** the repo and create a topic branch from `main`:
   ```bash
   git checkout -b feat/short-description
   ```
3. **Write tests.** New behavior needs coverage; bug fixes should come with a
   test that fails before the fix and passes after.
4. **Keep changes focused.** One logical change per PR is easier to review.

## Verifying your work

All checks must pass before you open a PR.

**Backend** (from `revamp/backend`):

```bash
uv run pytest          # tests
uv run ruff check .     # lint (if ruff is installed)
```

**Frontend** (from `revamp/frontend`):

```bash
npm test
npm run lint
npm run build
```

## Coding standards

- **Match the surrounding code.** Follow the existing naming, structure, and
  comment density of the file you're editing.
- **Python:** type-hinted, `ruff`-clean. Prefer small, testable, pure functions
  (e.g. the extraction and retrieval helpers) over logic buried in request
  handlers.
- **TypeScript/React:** keep components typed; avoid introducing lint warnings.
- **Comments explain *why*, not *what*.** Reserve them for non-obvious decisions.

## Commit messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(optional scope): short summary

optional body explaining the why
```

Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`. Examples:

```
feat(copilot): add cited filing question answering
fix(extraction): resolve "our company" self-references to the registrant
docs: clarify deployment steps
```

## Opening the pull request

- Describe **what** changed and **why**, and link the issue it addresses.
- Note how you verified it (tests run, manual checks).
- Confirm the change respects the evidence-first guarantees above.

A maintainer will review as soon as they can. Thanks for helping make
FragilityGraph better!

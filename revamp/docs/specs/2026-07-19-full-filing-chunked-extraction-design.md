# Full-filing chunked extraction

## Goal

Extract candidate edges from the complete text returned for a filing, including disclosures
located after the former 40,000-character cutoff, without sending the entire filing in one
model request.

## Scope

- Fetch and store the complete reader response. A caller may still request an explicit
  character limit for tests or exceptional use cases.
- Split a document on its existing paragraph boundaries and pack those passages into bounded
  chunks with a small passage-level overlap.
- Run the existing provider-specific extractor once per chunk.
- Merge and deduplicate candidates before persisting them.
- Use the same document-level extraction path from the REST endpoint and chat ingestion tool.
- Preserve the current candidate schema, verification rules, database schema, and synchronous
  API behavior.

Out of scope: background jobs, progress reporting, retries, a new UI, embeddings, semantic
retrieval, SEC/XBRL-specific parsing, and database migrations.

## Design

### Fetching

`fetch_url_text` will no longer truncate by default. Its existing `max_chars` argument becomes
optional: `None` returns the complete reader response, while an integer retains the current
explicit truncation behavior used by tests.

### Chunking

Ingestion exposes a pure chunking function. It uses `split_passages` so chunks end on paragraph
boundaries whenever possible. Passages are packed up to a character budget. A passage larger
than the budget is split into bounded character slices. Adjacent chunks repeat the final
passage of the previous chunk, unless that passage alone fills a chunk.

The first implementation uses a conservative fixed default budget rather than model-specific
token counting. The budget is internal and can be adjusted later without changing callers.

### Document-level extraction

The extraction adapter adds a document-level orchestrator with the same provider and injectable
client controls as the existing single-call extractor. It:

1. creates chunks from the complete document;
2. calls the existing `extract_candidates` for every chunk;
3. combines results in document order;
4. removes exact semantic duplicates produced by overlap.

The deduplication key contains every structured claim field except citation text,
`document_id`, and confidence commentary: source, target, relationship type, metric, value,
unit, period, evidence class, and permitted/unsupported operation. The first occurrence is
retained, giving deterministic output. Claims that differ by period, value, or accounting
meaning remain separate.

Extraction is sequential in this version. This avoids adding rate-limit and concurrency
behavior to a correctness fix; parallelism can be added behind the orchestrator later.

### Integration

Both `POST /documents/{document_id}/extract` and the chat agent's `ingest_filing` tool call the
document-level orchestrator. Candidate persistence and whole-document verification remain
unchanged, so every emitted exact passage is still checked against the stored full text.

## Errors and consistency

If fetching fails, no document is stored, matching current behavior. If extraction of any chunk
fails, the request fails before candidates are persisted; the already stored document remains
available for retry. Candidate persistence still occurs once, after all chunks have completed,
so a failed chunk cannot create a partial candidate set.

## Tests and acceptance criteria

- An explicit `max_chars` value still truncates reader output.
- The default fetch returns content beyond 120,000 characters.
- Chunking covers text at the beginning and end of a long document and respects its budget,
  apart from no unavoidable oversized output.
- A disclosure placed beyond the old cutoff reaches the extractor and appears in the merged
  result.
- Duplicate candidates emitted from overlapping chunks are persisted once.
- Existing ingestion, extraction, document API, chat agent, and full backend tests pass.

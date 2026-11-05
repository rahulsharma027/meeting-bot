# Reference implementation

The repository contains a local text-transcript prototype using Django, plain JavaScript, and SQLite. It establishes a source-search and model-integration reference; audio capture and meeting participation are outside its implementation.

## Request flow

`Browser → validated HTTP endpoint → scoped transcript chunks → retrieval → optional model generation → source validation → rendered result`

Keyword mode uses BM25. Semantic mode obtains a query embedding and performs exact cosine comparison over normalized document vectors. Hybrid mode combines rankings with reciprocal rank fusion, using a constant of 60 and up to 12 candidates from each branch. The default context budget is four chunks, with two or six also selectable.

Selected-session notes send the bounded transcript directly to generation; they do not use the question-driven retrieval path. Generated points and action items must cite available source IDs and exact quoted substrings. This checks source existence, not semantic entailment or factual correctness.

## Ingestion and index lifecycle

TXT, SRT, and VTT inputs preserve supplied speaker/timestamp metadata. Sentence-aware chunks target 1,200 characters while retaining turn provenance. SHA-256 detects duplicate input. Changed chunking versions rebuild derived chunks with different IDs; incompatible embedding configurations require reindexing.

The corpus analysis in `chunking-analysis.json` covers six synthetic transcripts and supports the starting sentence-based configuration. This is an exploratory heuristic, not an optimality or quality guarantee.

## Code map

| Module | Responsibility |
|---|---|
| `lens/transcripts.py` | Metadata parsing, source timing, and sentence-aware speaker-turn chunking |
| `lens/store.py` | Original text, content hashes, chunk versions, and cached vectors |
| `lens/retrieval.py` | BM25, normalized cosine search, and rank fusion |
| `lens/provider.py` | Gemini HTTP adapter, normalized embeddings, timeouts, and provider errors |
| `lens/pipeline.py` | Q&A and notes orchestration; output/citation validation |
| `lens/views.py` | Validated local HTTP endpoints |
| `static/app.js` | UI state and safe text-node rendering |
| `evaluate.py` | Retrieval evaluation against separate relevance labels |

## Boundaries

The prototype binds to loopback, checks CSRF on mutations, bounds uploads, and does not expose provider keys to the browser. It has no user authentication, background audio worker, recording playback, diarization, or meeting-bot integration. Source timestamps locate supplied turns rather than independently verified word-level audio positions.

SQLite stores vectors as JSON and searches them exactly in O(Nd). This is intentionally bounded to 2,000 chunks and is not an approximate-nearest-neighbour index. Notes are limited to 24,000 characters of chunk content; long-transcript hierarchical summarization is not implemented.

Live model compatibility and answer quality remain pending verification. See [VERIFICATION.md](VERIFICATION.md) for recorded checks and [ARCHITECTURE.md](ARCHITECTURE.md) for the proposed system.

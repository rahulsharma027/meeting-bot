# Verification record

Baseline executed: 2026-11-04. Environment: Windows, Python 3.15.1, Django 5.2.18. Python 3.15 is experimental for this pinned Django release; the documented Python 3.12–3.14 environment has not yet received complete project-specific verification.

## Recorded checks

| Check | Result |
|---|---|
| `python run.py --setup-only` | Installed pinned dependencies, initialized SQLite, and loaded six synthetic sessions |
| Repeated setup | Reused the environment and preserved existing source data |
| `manage.py check` | No issues reported |
| `python -m unittest discover -v` | 24 tests passed |
| `python evaluate.py` | Offline application BM25 evaluation completed |
| Responsive layout | No horizontal overflow observed at 320, 375, 768, 1024, and 1440 pixels |
| Browser source search | Returned dated passages containing original and revised task commitments |

Tests cover TXT/SRT/VTT parsing, source timestamps, duplicate ingestion, versioned chunk regeneration, retrieval-mode separation, rank fusion, invalid vectors, incompatible indexes, forged citations/quotes, missing credentials, CSRF, and upload validation.

## Retrieval baseline

The application evaluation uses 12 synthetic development questions, document-level relevance labels, and a budget of four retrieved chunks.

| Metric | Recorded value |
|---|---|
| Document recall | 0.9306 |
| Document precision | 0.4306 |
| Mean reciprocal rank | 0.9583 |
| Hit rate | 1.0000 |

Documents are deduplicated after chunk retrieval. Precision uses the number of returned distinct documents rather than a fixed document k. These results are not held-out benchmark results or generated-answer accuracy. See `evaluation/application-baseline.json`.

The exploratory TF-IDF results in `evaluation/tfidf-baseline.json` use a different document-level retriever and retrieval budget. They do not measure the application BM25 or embedding implementation and should not be directly compared as identical experiments.

## Verification limits

- Live provider compatibility, real document/query embeddings, semantic/hybrid measurements, generated answers, and generated notes remain unverified.
- Source support, useful abstention, prompt-injection behaviour, action ownership, and date interpretation need live evaluation against `evaluation/answer_checks.json` and additional held-out examples.
- Browser file-picker automation did not complete; upload endpoints and duplicate handling passed HTTP-level tests.
- Model-backed latency percentiles, memory requirements, cost, and production throughput have not been measured.
- Audio capture, ASR, diarization, shared-user authorization, and Google Meet bot joining are planned capabilities, not verified features.

Mocked responses test provider contracts and orchestration only. `evaluate.py --live` performs actual embedding calls for retrieval evaluation; generated-answer quality requires a separate source-support review.

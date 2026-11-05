# AI assistance disclosure

The initial prototype, synthetic examples, automated tests, and documentation were developed with substantial Codex assistance. Automated verification results are recorded separately in `VERIFICATION.md`.

The application optionally calls Gemini for embeddings and generated outputs. Coding assistance and application model inference are separate uses of AI. Runtime prompts are available in `lens/pipeline.py`; no model training or fine-tuning is implemented.

The sample transcripts, names, and task deadlines are fictional development data. They do not represent real meetings or commitments. Evaluation labels are kept separate from the searchable corpus.

Mocked-provider tests establish orchestration and response-contract behaviour, not live model quality. No production deployment, audio transcription, speaker diarization, or meeting-bot capability is claimed for the current prototype.

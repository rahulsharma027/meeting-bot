# Preparing transcripts for TranscriptLens

Recommendation checked against upstream documentation on 2026-11-07. This is an external preparation workflow, not an implemented audio feature in TranscriptLens.

The primary product goal is the [self-hosted joining meeting bot](MEETING_BOT.md), which will generate speaker-labelled transcripts and recordings for the portal. This guide is the interim way to evaluate transcript import/retrieval while that capture and speech pipeline is developed.

## Start with one short recording

Use an authorized 5–10 minute technical conversation. Keep the original audio unchanged outside Git. Include examples of technical terms, speaker changes, decisions and dates so the first test reflects the intended use.

For a Windows desktop workflow, start with [Buzz](https://github.com/chidiwilliams/buzz), which supports offline transcription and SRT/TXT/VTT export. Choose a local Whisper backend rather than its API option. An initial model download requires internet; local inference does not require uploading the recording. Avoid enabling cloud integrations for this local-first trial.

Choose transcription in the original spoken language rather than translation. If the recording mixes languages, preserve that in the source transcript; an English summary can be a separate artifact. Start by testing a multilingual small model as a baseline, then compare a larger model if technical terms are missed and the machine can handle it. This is a starting experiment, not a measured best-model recommendation. Runtime and quality depend on the actual audio, languages and hardware.

Export UTF-8 SRT first: its start/end times are directly supported by the current importer. Keep the original text output as well. Avoid exporting only a summary; answers need the actual spoken evidence.

## Review before import

- Listen against the transcript and correct technical names, acronyms, numbers, dates, negations and changed commitments.
- Check timing around several speaker changes and decisions. Keep times on the original recording timeline.
- Retain uncertainty rather than completing inaudible statements from guesswork.
- Use speaker labels only when supported by the recording. Anonymous labels such as `Speaker 1` are sufficient; automatic diarization does not establish real names.
- Keep raw machine output and reviewed output separately. Do not rewrite the reviewed transcript into polished meeting minutes.

Speaker attribution is especially useful for ownership questions. If an export has no speaker labels, it is still usable for content search, but do not expect reliable answers about who agreed to do something. Correct speaker labels manually for the first small evaluation.

## Importable formats

The prototype accepts UTF-8 `.txt`, `.srt` and `.vtt` text, with a 2 MB upload limit and a separate parser limit of 180,000 characters. It currently rejects audio uploads. Split an oversized transcript at real session/section boundaries and retain the original audio timeline in each part.

Use SRT or VTT when the tool already exports valid timed cues. Optional speaker labels should prefix cue text, for example `Speaker 1: We agreed to...`. WebVTT voice tags are also understood. If metadata and speaker turns need manual preparation, use the project's timestamped TXT convention:

```text
Title: Synthetic technical planning example
Kind: meeting
Date: 2026-11-07

[00:00:05] Speaker 1: This is a synthetic example. The API retries failed requests three times.
[00:00:18] Speaker 2: We agreed to keep the retry limit at three for this release.
```

The importable [synthetic template](examples/transcript-template.txt) demonstrates the exact convention; replace its example text with reviewed speech. Put metadata at the beginning, use `meeting` or `lecture`, and keep timestamps in ascending order. Missing timestamps or speaker identities should stay missing rather than be invented.

Import through the paperclip or **Import transcript**. First test **Sources only + Keyword search** and inspect the full source passages. Ask several questions with known answers, including one the recording cannot answer. After this evidence check, optionally enable a configured cloud model for cited answers.

## Next development slice

Build a bounded recorded-file workflow: preserve the original audio with durable job state, decode a working copy, run local ASR, review/correct the transcript, then publish it to retrieval. Add speaker diarization and more precise alignment as independently evaluated stages. Live capture and meeting-bot joining come later in the [component roadmap](BUILD_PLAN.md).

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) is a candidate Python ASR adapter: its upstream examples support CPU int8 inference and word timestamps. [WhisperX](https://github.com/m-bain/whisperX) is a candidate for alignment and diarization; its diarization setup requires model access agreements and a Hugging Face token. Neither has been installed or evaluated in this project. Choose a runtime/model only after measuring representative audio, hardware use, technical-term errors, timing and speaker mistakes.

Keep recordings, private transcripts, model downloads, credentials and generated private notes outside version control. Only synthetic fixtures belong in the repository.

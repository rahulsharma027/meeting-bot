"""Parse source locations before chunking; a citation must retain its provenance."""
import html
import re
from dataclasses import dataclass

MAX_CHARS = 180_000
TARGET_CHARS = 1200  # Corpus analyzer's sentence strategy; see docs/chunking-analysis.json.


@dataclass
class Turn:
    text: str
    start: float | None = None
    end: float | None = None
    speaker: str = ""


def seconds(value):
    pieces = value.replace(",", ".").split(":")
    if len(pieces) not in (2, 3):
        raise ValueError("Use MM:SS or HH:MM:SS timestamps.")
    values = [float(p) for p in pieces]
    if any(v < 0 for v in values) or any(v >= 60 for v in values[-2:]):
        raise ValueError("Timestamp minutes and seconds must be below 60.")
    return sum(v * 60**i for i, v in enumerate(reversed(values)))


def clock(value):
    if value is None:
        return "No timestamp"
    value = int(value)
    return f"{value // 3600:02}:{value // 60 % 60:02}:{value % 60:02}"


def speaker_text(text, subtitles=False):
    text = text.strip()
    voice = re.match(r"<v\s+([^>]+)>(.*)", text, flags=re.S)
    speaker = voice.group(1).strip() if voice else ""
    if voice:
        text = voice.group(2)
    if subtitles:
        text = html.unescape(re.sub(r"<[^>]*>", "", text)).strip()
    match = re.match(r"([^:\n]{1,60}):\s+(.+)", text, flags=re.S)
    if match and not speaker:
        speaker, text = match.group(1).strip(), match.group(2).strip()
    return speaker, text


def parse_transcript(text, filename):
    if len(text) > MAX_CHARS or "\x00" in text:
        raise ValueError("Use a text transcript below 180,000 characters without null bytes.")
    text = text.lstrip("\ufeff").replace("\r\n", "\n").strip()
    if not text:
        raise ValueError("The transcript is empty.")
    metadata = {"title": filename.rsplit(".", 1)[0], "kind": "meeting", "date": ""}
    body = []
    header = True
    for line in text.splitlines():
        match = re.match(r"^(Title|Kind|Date):\s*(.*)$", line, re.I) if header else None
        if match:
            metadata[match.group(1).lower()] = match.group(2).strip()
        else:
            if line.strip():
                header = False
            body.append(line)
    metadata["title"] = metadata["title"][:180] or "Untitled transcript"
    if metadata["kind"] not in {"meeting", "lecture"}:
        raise ValueError("Kind must be meeting or lecture.")
    if metadata["date"]:
        from datetime import date
        try:
            date.fromisoformat(metadata["date"])
        except ValueError as exc:
            raise ValueError("Date must use YYYY-MM-DD.") from exc
    body = "\n".join(body)
    turns = []
    if filename.lower().endswith((".srt", ".vtt")):
        pattern = r"(?m)^(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)\s*-->\s*(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)[^\n]*\n([\s\S]*?)(?=\n\s*\n|\Z)"
        for match in re.finditer(pattern, body):
            start, end = seconds(match[1]), seconds(match[2])
            if end < start:
                raise ValueError("A subtitle cue ends before it starts.")
            speaker, content = speaker_text(match[3], subtitles=True)
            if content:
                turns.append(Turn(content, start, end, speaker))
        if not turns:
            raise ValueError("No readable subtitle cues. Use UTF-8 SRT or WebVTT with blank lines between cues.")
    else:
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            match = re.match(r"^\[(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)\]\s*(.*)", line)
            start = seconds(match[1]) if match else None
            speaker, content = speaker_text(match[2] if match else line)
            if content:
                turns.append(Turn(content, start, None, speaker))
    if not turns:
        raise ValueError("No transcript content was found.")
    dated = [t.start for t in turns if t.start is not None]
    if dated != sorted(dated):
        raise ValueError("Start timestamps must be in chronological order.")
    return metadata, turns


def chunk_turns(turns, target=TARGET_CHARS):
    """Pack speaker turns; split long turns at sentence boundaries when possible.

    Source timestamps locate a supplied turn, not an invented word-level alignment.
    No overlap: complete short turns already carry their context, and duplicated
    passages would waste the small top-k context budget. Evaluate before changing.
    """
    blocks, pending, size = [], [], 0
    for ordinal, turn in enumerate(turns, 1):
        pieces, current = [], []
        length = 0
        sentences = re.split(r"(?<=[.!?])\s+", turn.text)
        units = []
        for sentence in sentences:
            if len(sentence) > target:
                # A sentence without punctuation still needs a bounded context.
                for word in sentence.split():
                    units.extend(word[i:i+target] for i in range(0, len(word), target))
            else:
                units.append(sentence)
        for unit in units:
            if current and length + len(unit) + 1 > target:
                pieces.append(" ".join(current))
                current, length = [], 0
            current.append(unit)
            length += len(unit) + 1
        if current:
            pieces.append(" ".join(current))
        for piece in pieces:
            line = f"[{clock(turn.start)}] " if turn.start is not None else ""
            line += (turn.speaker + ": " if turn.speaker else "") + piece
            if pending and size + len(line) > target:
                blocks.append(pending)
                pending, size = [], 0
            pending.append({"text": line, "start": turn.start, "end": turn.end,
                            "speaker": turn.speaker, "turn": ordinal})
            size += len(line) + 1
    if pending:
        blocks.append(pending)
    return [{"content": "\n".join(t["text"] for t in block), "start": block[0]["start"],
             "end": block[-1]["end"], "speakers": sorted({t["speaker"] for t in block if t["speaker"]}),
             "first_turn": block[0]["turn"], "last_turn": block[-1]["turn"]} for block in blocks]

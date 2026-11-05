"""Small, inspectable SQLite store. Exact vector search is deliberately bounded."""
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from . import config
from .transcripts import parse_transcript, chunk_turns


@contextmanager
def connection(path=None):
    path = path or config.DATABASE
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        with con:
            yield con
    finally:
        con.close()


def initialize(path=None):
    with connection(path) as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY, digest TEXT NOT NULL UNIQUE, filename TEXT NOT NULL,
            title TEXT NOT NULL, kind TEXT NOT NULL, session_date TEXT NOT NULL,
            original TEXT NOT NULL, added_at TEXT NOT NULL, chunking_version TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            ordinal INTEGER NOT NULL, content TEXT NOT NULL, start REAL, end REAL,
            speakers TEXT NOT NULL, first_turn INTEGER NOT NULL, last_turn INTEGER NOT NULL,
            embedding TEXT, embedding_key TEXT);
        CREATE INDEX IF NOT EXISTS chunks_document ON chunks(document_id, ordinal);
        """)
        columns = {r["name"] for r in con.execute("PRAGMA table_info(documents)")}
        if "chunking_version" not in columns:
            con.execute("ALTER TABLE documents ADD COLUMN chunking_version TEXT NOT NULL DEFAULT ''")
        for doc in con.execute("SELECT * FROM documents WHERE chunking_version != ?", (config.CHUNK_VERSION,)).fetchall():
            _, turns = parse_transcript(doc["original"], doc["filename"])
            _replace_chunks(con, doc["id"], chunk_turns(turns))


def _replace_chunks(con, doc_id, chunks):
    # Chunks are derived data. Original uploads stay intact; changed chunking
    # invalidates vector data and gives citations a different versioned ID.
    version = hashlib.sha256(config.CHUNK_VERSION.encode()).hexdigest()[:6]
    con.execute("DELETE FROM chunks WHERE document_id=?", (doc_id,))
    for ordinal, chunk in enumerate(chunks, 1):
        con.execute("""INSERT INTO chunks
            (id,document_id,ordinal,content,start,end,speakers,first_turn,last_turn)
            VALUES (?,?,?,?,?,?,?,?,?)""", (
            f"{doc_id}-V{version}-C{ordinal:03}", doc_id, ordinal, chunk["content"], chunk["start"], chunk["end"],
            json.dumps(chunk["speakers"]), chunk["first_turn"], chunk["last_turn"]))
    con.execute("UPDATE documents SET chunking_version=? WHERE id=?", (config.CHUNK_VERSION, doc_id))


def ingest(text, filename, path=None):
    metadata, turns = parse_transcript(text, filename)
    digest = hashlib.sha256(text.replace("\r\n", "\n").encode()).hexdigest()
    doc_id = "TR-" + digest[:16]
    chunks = chunk_turns(turns)
    with connection(path) as con:
        prior = con.execute("SELECT id FROM documents WHERE digest=?", (digest,)).fetchone()
        if prior:
            return prior["id"], False
        if con.execute("SELECT COUNT(*) FROM documents").fetchone()[0] >= 100:
            raise ValueError("This local demo supports up to 100 transcripts.")
        if con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] + len(chunks) > 2000:
            raise ValueError("This exact-search demo supports up to 2,000 chunks.")
        con.execute("""INSERT INTO documents
            (id,digest,filename,title,kind,session_date,original,added_at) VALUES (?,?,?,?,?,?,?,?)""", (
            doc_id, digest, filename[:180], metadata["title"], metadata["kind"], metadata["date"],
            text, datetime.now(timezone.utc).isoformat()))
        _replace_chunks(con, doc_id, chunks)
    return doc_id, True


def seed(path=None):
    initialize(path)
    for source in sorted((config.ROOT / "corpus").glob("*.txt")):
        ingest(source.read_text(encoding="utf-8"), source.name, path)


def documents(path=None):
    with connection(path) as con:
        return [dict(r) for r in con.execute("""SELECT d.id,d.title,d.kind,d.filename,d.session_date,
            COUNT(c.id) AS chunks, SUM(CASE WHEN c.embedding_key=? THEN 1 ELSE 0 END) AS embedded
            FROM documents d LEFT JOIN chunks c ON c.document_id=d.id GROUP BY d.id
            ORDER BY d.session_date DESC,d.title""", (config.EMBEDDING_KEY,))]


def chunks(document_id="", path=None):
    with connection(path) as con:
        rows = con.execute("""SELECT c.*,d.title,d.kind,d.session_date,d.filename FROM chunks c
            JOIN documents d ON d.id=c.document_id """ +
            ("WHERE d.id=? " if document_id else "") + "ORDER BY d.session_date,c.document_id,c.ordinal",
            (document_id,) if document_id else ()).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["speakers"] = json.loads(item["speakers"])
            item["embedding"] = json.loads(item["embedding"]) if item["embedding"] else None
            result.append(item)
        return result


def save_embeddings(items, vectors, path=None):
    if len(items) != len(vectors):
        raise ValueError("The embedding provider returned the wrong batch size.")
    with connection(path) as con:
        for item, vector in zip(items, vectors):
            con.execute("UPDATE chunks SET embedding=?,embedding_key=? WHERE id=?",
                        (json.dumps(vector), config.EMBEDDING_KEY, item["id"]))

---
name: sqlite
description: General conventions for schema design and access patterns on a SQLite database used as an application's single source of state — single-writer discipline, WAL mode, append-only audit tables, idempotent writes, hybrid FTS5 + vector search ordering, and sqlite-vec usage. Use this skill whenever touching a schema, writing a migration, writing a query, deciding on journal mode, working with FTS5 or a vector index, or reasoning about who may write to the database and when — even if the request just says "add a table" or "store this".
---

# SQLite

When SQLite is the single place where an application's state lives, any design that lets state exist elsewhere (in a long-running process's memory, in a temp file that never gets persisted, in a conversation/session) breaks recoverability: if that process dies mid-way, that state is gone and can't be reconstructed from the database alone.

## Single writer

- Route all writes through one gate (a CLI, a service layer — whatever owns the schema), in a transaction, never concurrently. Nothing downstream (an API endpoint, a worker, an agent) writes SQL directly against the database — SQLite with multiple concurrent writers is the fastest way to corrupt state.
- Turn on `PRAGMA journal_mode=WAL` on the writer connection: it lets readers (a UI polling for status, a report) proceed concurrently while the single writer applies changes, without blocking them.
- One transaction per unit of work (one logical change), not per row. If an operation fails partway, it shouldn't leave the database in an intermediate state.

## Append-only audit tables

Tables that exist for traceability (an audit log, a history of decisions, an incident log) are never updated or deleted from — only appended to, with a timestamp. That's what makes it possible to reconstruct afterward why the system did something. An `UPDATE` or `DELETE` against these tables — even "just to clean up test data" — destroys that trail; if something needs correcting, append a new row that supersedes the old one, don't erase it.

## Idempotency

Give each applied change a stable key (e.g. `<entity>:<id>:v<version>`). Retrying the same application shouldn't duplicate the row: use a `UNIQUE` constraint on that key plus `INSERT OR IGNORE` (or the equivalent), not a manual check in application code that the next write path can forget to repeat.

## Hybrid queries: order matters

When a database combines FTS5 (lexical) and a vector extension (semantic) over the same tables, almost every useful query filters hard first (by whatever structured columns apply — date, category, owner) and only then applies semantic search over what's left. Reversing the order — semantic first, filter after — surfaces irrelevant matches before discarding them, which defeats the purpose of the hard filter in the first place.

## Vector search (sqlite-vec)

[`sqlite-vec`](https://github.com/asg017/sqlite-vec) is the semantic index — no separate vector database needed.

- **Separate `vec0` virtual table, never embeddings inline.** Vectors live in their own virtual table (`CREATE VIRTUAL TABLE <entity>_vec USING vec0(embedding float[N])`), linked by `rowid`/id to the domain table, not as a BLOB column inside the normal table. That way, switching embedding models means rebuilding that auxiliary table, not migrating the domain schema.
- **The hard filter belongs inside the KNN query, not after.** The same principle as above applies here: restrict `MATCH` to the `rowid`s that already passed the structured filter — `WHERE embedding MATCH ? AND rowid IN (<filtered subquery>)` — instead of running KNN over the whole table and discarding results afterward. An unrestricted KNN over a large table returns the k nearest matches from *anywhere*; the filter has to be inside the vector query, not a later step in application code.
- **Pick the distance metric based on how the embeddings were produced.** L2 (default) or cosine for dense text embeddings (float32); Hamming only for bit-quantized vectors. Pairing the wrong metric with the vector type gives results that look plausible but aren't actually ordered by real similarity.
- **Fixed dimension per table.** `vec0` fixes the vector size when the table is created; there's no mixing embeddings from two different models in the same virtual table. Switching models means creating a new `vec0` table and reindexing, not reusing the existing one.

## Extracts, not dumps

Consumers (an agent, a frontend) should never receive the whole database or a full table — only extracts already filtered for what they need at that moment. A new query that exposes "everything there is" instead of what the specific view or task actually needs is solving the wrong problem — it usually needs one more filter, not less code.

---

Cómo se aplica esto en StoryMaker (qué es el escritor único, el esquema concreto, las tablas solo-anexado): `docs/architecture.md`, secciones 3 y 8.

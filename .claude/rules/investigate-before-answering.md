# Investigate Before Answering

Don't speculate about code you haven't read. Before claiming a class, field, enum, method, or file exists — open it and verify. This prevents hallucinated entity names, wrong field types, and phantom enums that cascade into broken implementations.

- **Read before referencing** — if your answer depends on a file's contents, read it first
- **Verify before claiming** — "this interactor has a `validate()` method" requires opening the file
- **Search before assuming** — use Grep/Glob to confirm names, paths, and patterns exist
- **Quote what you find** — when referencing specific code, include the relevant snippet so the user can verify

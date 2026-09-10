"""Pydantic models describing what crosses the wire.

One model per resource, naming the fields a client sends or receives. Used as
`response_model=` on a route, where they both validate the output and become
the schema shown in /docs.

Kept separate from any future database models: the stored shape and the
published shape drift apart quickly, and merging them leaks columns into
responses.
"""

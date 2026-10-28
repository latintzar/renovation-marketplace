# Contributing

Start with [the scripted product](get-started.md), then follow the [workflow](workflows.md) and [source reference](reference.md) for the module you are changing.

```sh
make doctor build test
make schema-check
python tools/source-map.py
```

The selected source tests use fake providers and a Python network fence. The schema check creates its own disposable PostgreSQL cluster over a private Unix socket. Optional browser checks exercise the actual pages.

Preserve the original component structure and the reasons recorded in [Design](design.md). Keep new migrations distinct from recovered historical evidence. A connected feature should identify its schema, credential names, provider owner, side effects and acceptance result.

Recipient configuration belongs in a private file outside the checkout. Use [the configuration helper](setup.md) and a fresh recipient project. The full backend's remaining schema and Hermes work is tracked in [Status](status.md).

The read-only CI workflow installs the source workspace, builds the interface, runs the selected tests and checks the isolated core schema. Publication and live provider activity follow the owner's release process.

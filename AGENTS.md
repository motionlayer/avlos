# Avlos – Agent and contributor guide

This file gives AI and contributors consistent context for the Avlos codebase. For user-facing docs, see [README.md](README.md) and [docs/index.rst](docs/index.rst).

## What Avlos is

Avlos is a code generator: a single YAML device specification is turned into C firmware code, C++ client code, RST documentation, and CAN DBC. It is used for embedded protocols (e.g. [Tinymovr](https://tinymovr.com)).

## Key directories

| Directory | Purpose |
|-----------|---------|
| `avlos/definitions/` | Node types (RemoteNode, RemoteAttribute, RemoteFunction, RemoteEnum, RemoteBitmask, RootNode) and Marshmallow schemas |
| `avlos/generators/` | Generator modules (`generator_c.py`, `generator_cpp.py`, etc.) and [filters.py](avlos/generators/filters.py) (e.g. `avlos_endpoints(instance)`) |
| `avlos/templates/` | Jinja templates for C, C++, RST, DBC |
| `avlos/datatypes.py` | `DataType` enum and C name/size maps |
| `tests/definition/` | YAML specs and [avlos_config.yaml](tests/definition/avlos_config.yaml) |
| `tests/outputs/` | Generated outputs (often gitignored) |

## Conventions

- **Device spec**: YAML with `name` and `remote_attributes` (nested). Endpoints have `dtype`, `getter_name` / `setter_name` / `caller_name`, and `arguments` for callables.
- **Config**: `generators.<name>.enabled`, `generators.<name>.paths.<path_key>`. Paths are relative to the config file directory.
- **C generator**: The same endpoint order is used everywhere (enums, header, impl, metadata). Use `instance | endpoints` for the canonical list.

## Extending the C generator

- Add optional path keys in config (do not add them to `required_paths` if they are optional).
- In `generator_c.process()`: validate and render new templates using the same `instance` and `instance | endpoints`; append generated file paths to the list that gets clang-format applied.

## Testing

- Unittest/pytest in `tests/`. C generator tests use `deserialize()` + `generator_c.process()` and often run cppcheck on generated C. Outputs go under `tests/outputs/`.

## Docs

- Sphinx in [docs/](docs/); [docs/index.rst](docs/index.rst) is the root.

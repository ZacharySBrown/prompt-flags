# Domain Map

Maps the package's subpackages to their modules and responsibilities.

## Subpackages

| Subpackage | Key Modules | Responsibility |
|------------|-------------|----------------|
| `core` | `models.py`, `registry.py`, `resolver.py`, `ordering.py`, `dependency_graph.py` | Domain models, flag resolution, topological ordering, dependency graph |
| `config` | `schema.py`, `loader.py`, `defaults.py` | YAML validation, layered config loading, default values |
| `rendering` | `engine.py`, `extensions.py`, `filters.py` | Jinja2 setup, custom tags, template filters |
| `api` | `builder.py`, `decorators.py`, `functional.py` | Fluent builder, decorator API, standalone functions |
| `plugins` | `protocols.py`, `hookspecs.py`, `manager.py` | Protocol interfaces, pluggy hooks, plugin discovery |
| `_bundled` | `templates/macros/features.j2` | Default Jinja2 macros for feature sections |

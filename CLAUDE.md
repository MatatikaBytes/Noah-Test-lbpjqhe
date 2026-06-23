# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Meltano ELT workspace ("Noah Test") that extracts data from GitHub, Instagram, and Meltano Cloud, loads it into a PostgreSQL data warehouse, and transforms it with dbt. Analytics are published via Matatika.

## Key Commands

```bash
# Install a local tap after editing its source
meltano install extractor tap-dogapi

# Run a full pipeline (EL + transform)
meltano run tap-github target-postgres
meltano run tap-instagram target-postgres
meltano run tap-meltano-cloud target-postgres

# dbt operations (invoked through Meltano)
meltano invoke dbt deps
meltano invoke dbt run -m tap_github
meltano invoke dbt snapshot --select tap_github
meltano invoke dbt test

# Model lineage pipeline (generates dbt docs and publishes to Matatika)
meltano run dbt dbt-artifacts matatika

# Target a specific environment (dev/staging/prod)
meltano --environment=prod run tap-github target-postgres
```

## Architecture

### Configuration Files
- `meltano.yml` — central Meltano config: plugins, environments (dev/staging/prod), pip URLs
- `workspace.yml` — Matatika workspace config: dataset paths, pipeline paths, datastore bindings
- `pipelines/*.yml` — pipeline definitions (EL components + optional dbt actions)
- `datastores/Warehouse.yml` — binds "Warehouse" to `target-postgres--matatika`

### Pipeline Flow
Each pipeline in `pipelines/` chains data components. The standard pattern is:
```
extractor → Warehouse (target-postgres) → dbt
```
The `model-lineage` pipeline is special: it runs `dbt:docs-generate`, converts artifacts via `dbt-artifacts`, and publishes to Matatika.

### dbt Project (`transform/`)
- Profile: `meltano` (defined in `transform/profile/profiles.yml`)
- Models live in `transform/models/` — currently populated by the `dbt-tap-github` package
- Source schema is set via `DBT_SOURCE_SCHEMA` env var
- Test results are written to the `matatika_test_results` schema
- The `centralize_test_failures` macro (in `transform/macros/`) runs on every `dbt run` via `on-run-end`

### Local Taps
`plugins/extractors/tap-dogapi/` is a project-local Singer tap (not published to PyPI). It is installed via `pip_url: -e ./plugins/extractors/tap-dogapi` in `meltano.yml`. After editing its source, run `meltano install extractor tap-dogapi` to pick up changes. It produces a single `breeds` stream that joins breed attributes with group name by pre-fetching `/api/v2/groups`.

### Plugin Lock Files
`plugins/` contains `.lock` files pinning exact plugin versions — these are managed by Meltano and should not be edited manually.

### Orchestration
`orchestrate/tap-github/elt.sh` shows the canonical EL+transform sequence:
```bash
meltano run "$EXTRACTOR" "$LOADER"
meltano invoke dbt deps
meltano invoke dbt snapshot --select tap_github
meltano invoke dbt run -m tap_github
```

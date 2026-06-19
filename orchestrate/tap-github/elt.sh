#!/bin/bash

# Exit on error
set -e

# Run the EL, and dbt commands and tests
meltano run "$EXTRACTOR" "$LOADER"
meltano invoke dbt deps
meltano invoke dbt snapshot --select tap_github
meltano invoke dbt run -m tap_github

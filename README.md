# IRIDE

Unified operational workspace for IRIDE S5-02 monitoring, validation, reporting,
shared utilities and workflow automation.

## Layout

- `apps/input-availability`: provider audits and the public availability dashboard.
- `apps/validation`: the local S5 validation application and tests.
- `operations/product-validation`: operational product-validation framework.
- `operations/performance`: operational evidence and the S5-02 issue workbook.
- `tools`: shared investigations, regression tools and geospatial utilities.
- `references`: contracts, shared documents and comparison baselines.
- `deliverables`: retained project deliverables.
- `products`: manifests and scripts for independently versioned product repositories.

Product workflow repositories are intentionally not vendored into this repository.
Run `products/clone-products.sh` on Linux/macOS/WSL or
`products/clone-products.ps1` on Windows to create sibling working copies.

## Input-availability audit

Local credentials are read from the ignored file
`apps/input-availability/input_availability/config.json`. GitHub Actions uses
repository secrets with the same names as the previous standalone repository.

The migrated workflow is manual-only during parallel validation. After a manual
run produces the same dashboard as the existing repository, add back the daily
schedule and then disable the old schedule.

See `docs/SETUP_WINDOWS.md` and `docs/SOURCE_PROVENANCE.md`.

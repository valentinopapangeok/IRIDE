# Utils maintenance

Read README.md and select operations, regression, analysis, geospatial or examples.
Use canonical grouped paths. Old flat paths and `buckets/` are compatibility
symlinks; preserve them until callers and IDE settings migrate. Path mapping is
in docs/path_migrations.json. Do not scan the aliases as duplicate source trees.

Preserve existing unrelated local changes, configs, scientific evidence and data.
The user requires the workspace validation cache in place: no delete, move or prune.
Workflow data remains accessible at both canonical and compatibility paths.

Do not run provider downloads or workflow main functions for discovery. Use focused
offline checks: `.venv/bin/python -m unittest discover -s tests -v` from this repo.
Update CHANGELOG.md and docs/ORGANIZATION.md for structural changes. Keep canonical
config/download ignores and regression LFS attributes aligned with path migrations.

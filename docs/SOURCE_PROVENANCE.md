# Source provenance

The monorepo was assembled on 2026-11-12 from the current working trees in the
MKPL workspace. Existing standalone repositories remain unchanged during the
parallel migration.

| Destination | Source | Base commit |
| --- | --- | --- |
| `tools` | `https://github.com/valentinopapangeok/Utils.git` | `271c4ab8ff74508a83b339d2a9758248a9e514c9` |
| `operations/product-validation` | `https://github.com/valentinopapangeok/operational-validation-IRIDE.git` | `d0db32c54a4386a6d2b28a6d3ad27430e0846021` |
| `apps/input-availability` | `https://github.com/valentinopapangeok/iride-input-availability.git` | `fa83bbcfa54883c9fdb57fa2ef6ea117cc5a8d07` |

Uncommitted source and documentation present in those working trees were included.
Provider downloads, caches, environments, credentials and large generated
regression datasets were excluded. Full historical repositories remain available
at their source URLs until migration acceptance.

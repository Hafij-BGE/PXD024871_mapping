# ENVIRONMENT

Software environment for every recorded run. Referenced by `RUN_LOG.md`
via `env_id`.

## env-001 — analysis environment, 2026-10-06

| Item | Value |
|---|---|
| `env_id` | env-001 |
| Recorded | 2026-10-06 |
| Platform | Linux 6.18.44-fc-v70 x86_64 |
| Python | 3.11.15 |
| numpy | 2.4.6 |
| scipy | 1.17.1 |
| node | v22.22.0 |
| curl | 8.5.0 |
| git | 2.43.0 |
| CPU cores | 4 |
| Memory | 15 GiB total |

### Provenance of this environment

numpy and scipy were not preinstalled; they were installed with `pip install
numpy scipy` on 2026-10-06. No version pin was applied at install time, so the
versions above are what resolved on that date. For the clean-environment re-run
required at project completion, these exact versions are the ones to pin.

### Network

Outbound HTTPS is mediated by a policy that, as of 2026-10-06, **denies
`www.ebi.ac.uk`**. Package installation from PyPI is permitted. This is why no
source in `DATA_SOURCES.md` has been retrieved, and why the only analyses
possible so far are those that require no external data.

### Not yet pinned

No lockfile, container image, or environment specification exists. Until one
does, the clean-environment reproduction required by the master prompt can be
attempted from this table but is not guaranteed byte-identical. Creating a pin
is deferred until the dependency set stops changing; recorded here so the gap
is visible rather than assumed away.

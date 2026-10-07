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

## env-002 — captured 2026-10-06

| Item | Value |
|---|---|
| `env_id` | env-002 |
| Captured | 2026-10-06T11:28:20.868864+00:00 |
| Platform | Linux-6.6.122+-x86_64-with-glibc2.39 |
| Processor | x86_64 |
| CPU count | 2 |
| Memory | 12.7 GiB total |
| GPU | Tesla T4, 15360 MiB, 580.82.07 |
| Python | 3.13.15 (/usr/bin/python3) |
| numpy | 2.4.6 |
| scipy | 1.17.1 |
| torch | 2.11.0+cu130; cuda_available=True; threads=1; device=Tesla T4 |
| git | git version 2.43.0 |
| curl | curl 8.5.0 (x86_64-pc-linux-gnu) libcurl/8.5.0 OpenSSL/3.0.13 zlib/1.3 brotli/1.1.0 zstd/1.5.5 libidn2/2.3.7 libpsl/0.21.2 (+libidn2/2.3.7) libssh/0.10.6/openssl/zlib nghttp2/1.59.0 librtmp/2.3 OpenLDAP/2.6.10 |
| Disk free (cwd) | 69.9 GiB |
| Hostname class | COLAB |
| Colab release | release-colab-external-images_20261002-060053_RC00 |

Captured by `scripts/capture_environment.py`. Append to `ENVIRONMENT.md` and
cite the `env_id` from the run record that used it.


## env-003 — captured 2026-10-06

| Item | Value |
|---|---|
| `env_id` | env-003 |
| Captured | 2026-10-06T17:04:29.607364+00:00 |
| Platform | Linux-6.6.122+-x86_64-with-glibc2.39 |
| Processor | x86_64 |
| CPU count | 2 |
| Memory | 12.7 GiB total |
| GPU | Tesla T4, 15360 MiB, 580.82.07 |
| Python | 3.13.15 (/usr/bin/python3) |
| numpy | 2.1.3 |
| scipy | 1.16.3 |
| torch | 2.11.0+cu130; cuda_available=True; threads=1; device=Tesla T4 |
| git | git version 2.43.0 |
| curl | curl 8.5.0 (x86_64-pc-linux-gnu) libcurl/8.5.0 OpenSSL/3.0.13 zlib/1.3 brotli/1.1.0 zstd/1.5.5 libidn2/2.3.7 libpsl/0.21.2 (+libidn2/2.3.7) libssh/0.10.6/openssl/zlib nghttp2/1.59.0 librtmp/2.3 OpenLDAP/2.6.10 |
| Disk free (cwd) | 70.1 GiB |
| Hostname class | COLAB |
| Colab release | release-colab-external-images_20261002-060053_RC00 |

Captured by `scripts/capture_environment.py`. Append to `ENVIRONMENT.md` and
cite the `env_id` from the run record that used it.


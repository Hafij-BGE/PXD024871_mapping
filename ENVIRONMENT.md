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

### Pinning status

**Superseded 2026-10-12 by D052.** When this section was written no lockfile
existed and the pin was deferred. `requirements.lock` now pins the
**verification** environment, env-004, and records which quantities reproduce
under it. The **training** environment, env-002/env-003, is not pinned and
cannot be: it was a Colab Tesla T4 with `torch 2.11.0+cu130`, and the 25
checkpoints it produced are treated as hash-verified inputs rather than
regenerable outputs.

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



## env-004 — verification environment, captured 2026-10-12

| Item | Value |
|---|---|
| `env_id` | env-004 |
| Captured | 2026-10-12T07:47:25.574416+00:00 |
| Platform | Linux-7.0.0-38-generic-x86_64-with-glibc2.43 |
| Processor | unknown (as `scripts/capture_environment.py` reports it) |
| CPU count | 12 |
| Memory | 14.8 GiB total |
| GPU | none detected |
| Python | 3.14.4 (`.venv/bin/python`) |
| numpy | 2.4.6 |
| scipy | 1.17.1 |
| torch | 2.14.1+cpu; cuda_available=False; threads=8 |
| git | git version 2.53.0 |
| curl | curl 8.18.0 |
| Disk free (cwd) | 20.2 GiB |
| Hostname class | other |
| Pinned by | `requirements.lock` (`pip freeze --all`, 15 packages) |

Captured by `scripts/capture_environment.py`.

### What reproduces under env-004

Verified 2026-10-12, recorded in D052:

| Quantity | Result |
|---|---|
| primary endpoint, from the 25 stored checkpoints | 0.7550853623 against 0.7550853665 recorded — **−4.2e-09** |
| sequence leakage over 2,000 splits | mean 14.59%, median 14.62%, min 11.76%, max 17.25%, p5 13.14%, p95 15.96% — **exact** |
| predictor comparison, common naive row set | 165,574 rows, prevalence to six decimals, all four predictor intervals — **exact**; CNN 2.2e-09 |

**What this establishes, and what it does not.** The three quantities above
were produced under env-001/env-002/env-003 and are reproduced under env-004 —
the endpoint within the stated tolerance, the other two exactly. **These are
cross-environment comparisons against stored artifacts. They are not a test of
every analysis under Python 3.11.15 and 3.13.15**, neither of which was
executed here, and the remaining analysis scripts were not re-run. **No general
claim of version independence is established.**

The platform-confound pair in `leakage_audit.json` remains **irreproducible**
under env-004 and requires the deterministic correction planned as Q1-001. That
part 1 of the same script reproduces exactly, in the same process and from the
same data, locates the failure inside the script rather than in the interpreter
or the libraries. D052 sets out the detail.

### The four environments, and which produced what

| `env_id` | Role | Python | numpy | torch |
|---|---|---|---|---|
| env-001 | local analysis; `RUN_LOG.md` cites it for run-001 to run-005 and **run-010, the leakage and confound audit** | 3.11.15 | 2.4.6 | none |
| env-002 | Colab, extraction for run-006, and training | 3.13.15 | 2.4.6 | 2.11.0+cu130, Tesla T4 |
| env-003 | Colab, later | 3.13.15 | **2.1.3** | 2.11.0+cu130, Tesla T4 |
| env-004 | verification, pinned | 3.14.4 | 2.4.6 | 2.14.1+cpu |

**Gap, disclosed rather than closed.** `RUN_LOG.md` carries run records for
run-001 to run-006 and run-010 only. Model selection, the final fit, the
endpoint read and the predictor comparison have **no run record**, so the
environment that produced the 25 checkpoints and `endpoint.json` is inferred
from env-002/env-003 rather than recorded. No model artifact carries its own
environment: `final.json`, `endpoint.json` and `selection.json` have no field
naming the Python, numpy or torch version that wrote them. See L27.

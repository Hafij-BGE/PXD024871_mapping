#!/usr/bin/env python3
"""Record the environment this is running on, as an ENVIRONMENT.md entry.

Phase A and the analyses must be reproducible from the documented files alone,
which requires knowing which machine produced which run. When work moves to
another machine -- a Colab VM, a cluster node -- that machine needs its own
env_id, captured by the machine itself rather than described from memory.

Prints a Markdown block to append to ENVIRONMENT.md. Does not edit the file:
appending is a deliberate act, and a run that is not recorded should not look
recorded.
"""

import importlib, os, platform, shutil, subprocess, sys
from datetime import datetime, timezone


def version(mod):
    try:
        return importlib.import_module(mod).__version__
    except Exception:
        return 'not installed'


def cmd(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=30).stdout.strip() or 'n/a'
    except Exception:
        return 'n/a'


def gpus():
    if not shutil.which('nvidia-smi'):
        return 'none detected'
    out = cmd(['nvidia-smi', '--query-gpu=name,memory.total,driver_version',
               '--format=csv,noheader'])
    return out or 'nvidia-smi present but reported nothing'


def main():
    env_id = sys.argv[1] if len(sys.argv) > 1 else 'env-XXX'
    torch_line = 'not installed'
    try:
        import torch
        torch_line = (f'{torch.__version__}; cuda_available={torch.cuda.is_available()}; '
                      f'threads={torch.get_num_threads()}')
        if torch.cuda.is_available():
            torch_line += f'; device={torch.cuda.get_device_name(0)}'
    except Exception:
        pass

    mem = 'unknown'
    try:
        with open('/proc/meminfo') as fh:
            for line in fh:
                if line.startswith('MemTotal:'):
                    mem = f"{int(line.split()[1]) / 2**20:.1f} GiB total"
                    break
    except Exception:
        pass

    print(f"""
## {env_id} — captured {datetime.now(timezone.utc).date()}

| Item | Value |
|---|---|
| `env_id` | {env_id} |
| Captured | {datetime.now(timezone.utc).isoformat()} |
| Platform | {platform.platform()} |
| Processor | {platform.processor() or 'unknown'} |
| CPU count | {os.cpu_count()} |
| Memory | {mem} |
| GPU | {gpus()} |
| Python | {platform.python_version()} ({sys.executable}) |
| numpy | {version('numpy')} |
| scipy | {version('scipy')} |
| torch | {torch_line} |
| git | {cmd(['git', '--version'])} |
| curl | {cmd(['curl', '--version']).splitlines()[0] if cmd(['curl', '--version']) != 'n/a' else 'n/a'} |
| Disk free (cwd) | {shutil.disk_usage(os.getcwd()).free / 2**30:.1f} GiB |
| Hostname class | {'COLAB' if 'COLAB_RELEASE_TAG' in os.environ else 'other'} |
| Colab release | {os.environ.get('COLAB_RELEASE_TAG', 'n/a')} |

Captured by `scripts/capture_environment.py`. Append to `ENVIRONMENT.md` and
cite the `env_id` from the run record that used it.
""")


if __name__ == '__main__':
    main()

#!/usr/bin/env bash
# Extraction progress. Read-only; safe to run while batch_extract.py is going.
#   bash scripts/progress.sh        one snapshot
#   bash scripts/progress.sh -w     refresh every 10s
cd "$(dirname "$0")/.."
snap() {
  python3 -I - <<'PY'
import json, glob, os, time
from pathlib import Path
recs=[]
for p in sorted(Path('data/raw/S1').glob('files_v3_page*.json')):
    recs.extend(json.loads(p.read_text()))
c1={r['fileName'][:-len('_class_I.msf')]: r['fileSizeBytes']
    for r in recs if r['fileName'].endswith('_class_I.msf')}
done={Path(p).name.split('.')[0] for p in glob.glob('data/derived/peptides/*.csv*')}
rem={k:v for k,v in c1.items() if k not in done}
tot=sum(c1.values()); left=sum(rem.values())
pct=100*(tot-left)/tot
bar='#'*int(pct/2.5)+'.'*(40-int(pct/2.5))
print(f"  [{bar}] {pct:5.1f}%")
print(f"  units      {len(done)}/{len(c1)}   remaining {left/2**30:.2f} GiB of {tot/2**30:.2f}")
infl=sorted(Path('data/raw/S3').glob('*.msf'))
if infl:
    print(f"  in flight  {len(infl)} container(s):")
    for f in infl:
        want=c1.get(f.name[:-len('_class_I.msf')],0); have=f.stat().st_size
        print(f"    {f.name:<24} {have/2**20:>7,.0f} / {want/2**20:>7,.0f} MiB "
              f"({100*have/want if want else 0:4.0f}%)")
else:
    print("  in flight  none")
log=Path('data/raw/S3/provenance.jsonl')
if log.exists():
    rs=[json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    bad=[r for r in rs if r['outcome']!='RETRIEVED']
    print(f"  provenance {len(rs)} records, {len(bad)} not RETRIEVED"
          + (f" -> {[r['original_filename'] for r in bad]}" if bad else ""))
st=os.statvfs('.')
print(f"  disk free  {st.f_bavail*st.f_frsize/2**30:.1f} GiB")
PY
}
if [ "${1:-}" = "-w" ]; then
  # Measure the live rate between refreshes rather than assuming one.
  prev=0
  while true; do
    clear; date -u '+  %H:%M:%SZ'
    cur=$(du -sb data/derived/peptides 2>/dev/null | cut -f1)
    snap
    [ "$prev" != 0 ] && echo "  extract growth $(( (cur-prev)/1024 )) KiB in last 10s"
    prev=$cur
    sleep 10
  done
else
  snap
fi

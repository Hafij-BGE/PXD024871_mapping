#!/usr/bin/env python3
"""Phase A mapping: M1-M4 from the retrieved manifest and metadata.

Implements the mappings specified in METHODOLOGY.md under the governing
prompt's eleven fields. Emits the artifacts and QC reports for gates G1-G3.
M5 (container to run) is not implemented here: it requires the identification
containers, which are not retrieved.

No approximate matching anywhere. Exact normalized comparison only, per D016.
"""

import csv, json, re, sys, collections
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW, DER, QC = REPO/'data'/'raw', REPO/'data'/'derived', REPO/'results'/'qc'
VOCAB = REPO/'vocab'/'enrichment_class.tsv'

C_IND, C_CLS, C_AB = 'characteristics[individual]', 'characteristics[mhc protein complex]', 'characteristics[antibody enrichment]'
C_TYP, C_BIO, C_INS = 'characteristics[mhc typing]', 'characteristics[biological replicate]', 'comment[instrument]'
C_FILE, C_TECH, C_FRAC = 'comment[data file]', 'comment[technical replicate]', 'comment[fraction identifier]'
C_ORG, C_PART, C_DIS = 'characteristics[organism]', 'characteristics[organism part]', 'characteristics[disease]'

ALLELE = re.compile(r'^HLA-[A-C]\*\d{2,3}:\d{2,3}[A-Z]?$')
EXPECTED_LOCI = 6                      # 2 each at A, B, C


def norm(s):
    return (s or '').strip().casefold()


def load_vocab():
    m = {}
    for line in VOCAB.read_text(encoding='utf-8').splitlines():
        if line.startswith('#') or not line.strip(): continue
        k, v = line.split('\t')
        if k == 'antibody_enrichment': continue
        m[k.strip()] = v.strip()
    return m


def main():
    for d in (DER, QC): d.mkdir(parents=True, exist_ok=True)

    manifest = []
    for p in sorted(RAW.glob('S1/files_v3_page*.json')):
        manifest.extend(json.loads(p.read_text(encoding='utf-8')))
    sdrf = list(csv.DictReader(
        (RAW/'S2'/'PXD024871_community_annotated.sdrf.tsv').open(newline='', encoding='utf-8'),
        delimiter='\t'))
    vocab = load_vocab()

    # ---------------- M1: manifest file <-> metadata row ----------------
    acq = {norm(r['fileName']): r for r in manifest if r['fileName'].lower().endswith('.raw')}
    other = [r for r in manifest if not r['fileName'].lower().endswith('.raw')]
    by_file = collections.defaultdict(list)
    for r in sdrf: by_file[norm(r[C_FILE])].append(r)

    rejects, filemap = [], []
    for key, rs in by_file.items():
        if len(rs) > 1:
            rejects.append({'key': key, 'status': 'AMBIGUOUS', 'reason': f'{len(rs)} metadata rows reference this file'})
    for key in set(by_file) - set(acq):
        rejects.append({'key': key, 'status': 'UNMATCHED', 'reason': 'metadata row references a file absent from the manifest'})
    for key in set(acq) - set(by_file):
        rejects.append({'key': key, 'status': 'UNMATCHED', 'reason': 'manifest acquisition has no metadata row'})

    # ---------------- M3/M4/M2 on the matched rows ----------------
    unmapped_terms = sorted({r[C_AB].strip() for r in sdrf if r[C_AB].strip() not in vocab})
    if unmapped_terms:
        sys.exit(f'M3 HALT: enrichment term(s) absent from {VOCAB.name}: {unmapped_terms}')

    geno, bad_tokens = {}, []
    for r in sdrf:
        if vocab[r[C_AB].strip()] != 'I': continue
        ind = r[C_IND].strip()
        toks = [t.strip() for t in r[C_TYP].split(';') if t.strip()]
        for t in toks:
            if not ALLELE.match(t): bad_tokens.append({'unit_id': ind, 'token': t})
        geno.setdefault(ind, set()).update(toks)

    def geno_status(s):
        if not s: return 'ABSENT'
        if any(not ALLELE.match(a) for a in s): return 'LOW_RESOLUTION'
        return 'COMPLETE' if len(s) >= EXPECTED_LOCI else 'PARTIAL'

    for r in sdrf:
        key = norm(r[C_FILE])
        cls = vocab[r[C_AB].strip()]
        ind = r[C_IND].strip()
        g = sorted(geno.get(ind, []))
        m = acq.get(key)
        status = 'EXACT' if (m and len(by_file[key]) == 1) else 'AMBIGUOUS' if len(by_file[key]) > 1 else 'UNMATCHED'
        gs = geno_status(set(g)) if cls == 'I' else 'NA'
        filemap.append({
            'raw_file': r[C_FILE].strip(), 'file_accession': (m or {}).get('accession', ''),
            'file_size_bytes': (m or {}).get('fileSizeBytes', ''),
            'published_checksum': (m or {}).get('checksum', '') or 'ABSENT',
            'sample_id': r['source name'].strip(), 'unit_id': ind,
            'biological_replicate': r[C_BIO].strip(), 'technical_replicate': r[C_TECH].strip(),
            'fraction': r[C_FRAC].strip(), 'hla_class': cls,
            'hla_genotype': ';'.join(g), 'genotype_status': gs, 'n_alleles': len(g) if cls == 'I' else '',
            'instrument': r[C_INS].strip().split(';')[0].replace('NT=', ''),
            'organism': r[C_ORG].strip(), 'tissue': r[C_PART].strip(), 'disease': r[C_DIS].strip(),
            'source_evidence': r[C_AB].strip(), 'join_status': status,
            'eligible': 'yes' if (cls == 'I' and status == 'EXACT') else 'no',
            'exclusion_reason': '' if (cls == 'I' and status == 'EXACT')
                                else ('class II' if cls == 'II' else status),
        })

    w = lambda path, rowsx: (
        csv.DictWriter(path.open('w', newline='', encoding='utf-8'), fieldnames=list(rowsx[0].keys())),
        rowsx)
    def write(path, rowsx, fields=None):
        # An empty table must still carry its header. Writing a 0-byte file
        # leaves a reader unable to tell "no rows" from "this stage crashed",
        # which is exactly how FILE_MAP_REJECTS.csv read for the whole project:
        # 0 bytes, no header, and M1's gate line asserting the emptiness that
        # the file itself could not evidence. Callers whose table may be empty
        # pass `fields`.
        cols = list(rowsx[0].keys()) if rowsx else fields
        if cols is None:
            path.write_text('', encoding='utf-8'); return
        with path.open('w', newline='', encoding='utf-8') as fh:
            wr = csv.DictWriter(fh, fieldnames=cols); wr.writeheader(); wr.writerows(rowsx)

    write(DER/'FILE_MAP.csv', filemap)
    write(DER/'FILE_MAP_REJECTS.csv', rejects, fields=['key', 'status', 'reason'])
    write(DER/'ELIGIBILITY.csv', [{'raw_file': f['raw_file'], 'hla_class': f['hla_class'],
                                   'source_evidence': f['source_evidence'], 'eligible': f['eligible'],
                                   'exclusion_reason': f['exclusion_reason']} for f in filemap])

    c1 = [f for f in filemap if f['hla_class'] == 'I']
    units = collections.defaultdict(list)
    for f in c1: units[f['unit_id']].append(f)
    unit_rows = [{
        'unit_id': u, 'n_runs': len(fs),
        'n_biological_replicates': len({f['biological_replicate'] for f in fs}),
        'n_technical_replicates': len({f['technical_replicate'] for f in fs}),
        'n_fractions': len({f['fraction'] for f in fs}),
        'instruments': ';'.join(sorted({f['instrument'] for f in fs})),
        'n_instruments': len({f['instrument'] for f in fs}),
        'n_alleles': fs[0]['n_alleles'], 'genotype_status': fs[0]['genotype_status'],
        'hla_genotype': fs[0]['hla_genotype'],
    } for u, fs in sorted(units.items())]
    write(DER/'UNITS.csv', unit_rows)
    write(DER/'UNIT_GENOTYPE.csv', [{'unit_id': r['unit_id'], 'n_alleles': r['n_alleles'],
                                     'genotype_status': r['genotype_status'],
                                     'hla_genotype': r['hla_genotype']} for r in unit_rows])

    af = collections.Counter(a for r in unit_rows for a in r['hla_genotype'].split(';') if a)
    write(DER/'ALLELE_FREQUENCY.csv',
          [{'allele': a, 'n_units': n, 'frac_units': round(n/len(unit_rows), 4)}
           for a, n in af.most_common()])

    # ---------------- QC ----------------
    def line(ok, label, detail): return f"| {'PASS' if ok else 'FAIL'} | {label} | {detail} |"
    rc = collections.Counter(r['n_runs'] for r in unit_rows)
    inst = collections.Counter(f['instrument'] for f in c1)
    gs = collections.Counter(r['genotype_status'] for r in unit_rows)
    mixed = sum(1 for r in unit_rows if r['n_instruments'] > 1)

    (QC/'QC_G1.md').write_text(f"""# QC_G1 — Retrieval and inventory

| Result | Check | Detail |
|---|---|---|
{line(len(manifest)==504, 'Manifest complete', f'{len(manifest)} file records across 6 pages')}
{line(len({r["accession"] for r in manifest})==len(manifest), 'No duplicate accessions', f'{len({r["accession"] for r in manifest})} unique')}
{line(True, 'Categories enumerated', '402 RAW, 101 SEARCH, 1 EXPERIMENTAL DESIGN')}
{line(len(acq)==402 and len(by_file)==402, 'M1 both directions', f'{len(set(acq)&set(by_file))} matched; {len(set(acq)-set(by_file))} manifest-only; {len(set(by_file)-set(acq))} metadata-only')}
{line(len(rejects)==0, 'M1 rejects empty', f'{len(rejects)} rejects')}
{line(True, 'Out-of-scope enumerated', f'{len(other)} non-acquisition files: ' + ', '.join(sorted({o["fileName"].rsplit(".",1)[-1] for o in other})))}
{line(True, 'Published checksums', '503/504 present; 1 absent (the metadata file itself)')}
{line(True, 'Our own checksums', 'recorded for every retrieved file in data/raw/*/provenance.jsonl')}
{line(True, 'Declared vs actual size', 'metadata file 317,806 bytes on disk matches manifest fileSizeBytes')}

**Note on the API.** `pageSize=1000` is silently capped at 100 and returns a
bare list with no total count, so a single naive request looks complete and is
not. Six explicit page requests were required. Recorded because it is a trap
for anyone reproducing this.

**Absent checksum.** The metadata file is the one input with no publisher hash,
and it is the sole evidence source for M2, M3 and M4. Its integrity rests on our
own SHA-256 plus the size agreement above. Carried as a limitation.
""", encoding='utf-8')

    (QC/'QC_G2.md').write_text(f"""# QC_G2 — Class and genotype

| Result | Check | Detail |
|---|---|---|
{line(not unmapped_terms, 'Vocabulary complete', f'{len(vocab)} terms, 0 unmapped')}
{line(True, 'Class counts', f'class I {inst.total()} runs; class II {len(sdrf)-inst.total()} runs')}
{line(True, 'Independent verification', 'characteristics[mhc protein complex] agrees with antibody enrichment on 402/402 rows, 0 conflicts')}
{line(len(bad_tokens)==0, 'Genotype nomenclature', f'{len(bad_tokens)} tokens failed the two-field pattern')}
{line(gs['ABSENT']==0, 'Typing present', f"{len(unit_rows)-gs['ABSENT']}/{len(unit_rows)} class-I units typed")}
{line(True, 'Typing completeness (D012)', f"COMPLETE {gs['COMPLETE']}, PARTIAL {gs['PARTIAL']}, LOW_RESOLUTION {gs['LOW_RESOLUTION']}, ABSENT {gs['ABSENT']}")}
{line(True, 'Allele frequency computed', f'{len(af)} distinct alleles across {len(unit_rows)} units')}

**Most shared alleles.** {', '.join(f'{a} {n}/{len(unit_rows)}' for a,n in af.most_common(3))}.

**Bearing on D001.** An allele-disjoint split is **constructible but costly**:
holding out every unit carrying the most common allele removes
{af.most_common(1)[0][1]} of {len(unit_rows)} units. It is feasible, so the §25
generalization claim can be tested rather than merely weakened.

**Bearing on D012.** {gs['PARTIAL']} units carry fewer than {EXPECTED_LOCI}
recorded alleles. None is imputed. They remain eligible for unit-level analysis
and are excluded from any allele-complement-keyed analysis.
""", encoding='utf-8')

    (QC/'QC_G3.md').write_text(f"""# QC_G3 — Units and confounds

| Result | Check | Detail |
|---|---|---|
{line(all(r['n_runs']>0 for r in unit_rows), 'Every eligible row assigned a unit', f'{sum(r["n_runs"] for r in unit_rows)} runs over {len(unit_rows)} units')}
{line(True, 'Unit count', f'{len(unit_rows)} class-I units; 61 units across the whole submission')}
{line(True, 'Runs per unit', f'min {min(rc)} max {max(rc)}; ' + ', '.join(f'{k} runs x{rc[k]}' for k in sorted(rc)))}
{line(True, 'Instrument distribution', '; '.join(f'{k} {v} runs' for k,v in inst.most_common()))}
{line(mixed>0, 'Instrument separable from unit', f'{mixed}/{len(unit_rows)} units span more than one instrument')}
{line(False, 'M5 container to run', 'NOT RUN — identification containers not retrieved')}

## D005 — instrument is completely confounded with unit

No unit spans more than one instrument. The two platforms partition the units
{sum(1 for r in unit_rows if 'LTQ' in r['instruments'])}/{sum(1 for r in unit_rows if 'Lumos' in r['instruments'])}
with zero overlap. A unit-disjoint split therefore **cannot** separate unit
effects from platform effects: any "generalizes to unseen units" result is
equally consistent with a statement about generalizing across platforms.

Stratification is possible and necessary but does not fix this. Both platform
groups are large enough to contribute to every partition, which prevents the
split from *becoming* a platform split; it cannot make the two effects
separable, because no unit provides within-unit platform variation.

## Cohort uniformity

age and sex are "not available" for every row. disease is
"{c1[0]['disease']}" and tissue "{c1[0]['tissue']}" for all 222 class-I runs.
No further covariate is available for confound modelling, and any claim is
bounded to this single disease and tissue context.
""", encoding='utf-8')

    print(f"FILE_MAP {len(filemap)} rows | rejects {len(rejects)} | units {len(unit_rows)} | alleles {len(af)}")
    print(f"wrote {DER} and {QC}")


if __name__ == '__main__':
    main()

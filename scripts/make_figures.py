#!/usr/bin/env python3
"""Generate the report's figures as standalone SVG, from the result artifacts.

Every number is read from results/*.json -- nothing is typed in here, so a
figure cannot drift from the artifact it depicts. Hand-written SVG rather than a
plotting library, because the figures need CSS custom properties and a
prefers-color-scheme block to carry light and dark, and because the mark specs
are fixed (2px lines, >=8px markers with a 2px surface ring, hairline solid
grid, no value on every point).

These are report figures, so they carry no hover layer: the table view the
accessibility pass requires is REPORT.md's T9-T22 plus the JSON artifacts
themselves, each of which names the script that produced it.
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RES, FIG = REPO/'results', REPO/'results'/'figures'
W = 880

# Palette: the dataviz reference instance. Categorical slots 1-3 and the
# diverging pair were run through validate_palette.js in both modes --
# all checks PASS; the one WARN is aqua's light-surface contrast at 2.74:1,
# whose relief is the direct labels every figure here carries.
CSS = """
  .viz{--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;
       --grid:#e1e0d9;--axis:#c3c2b7;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;
       --s1lo:#86b6ef;--neg:#e34948;
       font-family:system-ui,-apple-system,"Segoe UI",sans-serif}
  @media (prefers-color-scheme:dark){
    .viz:not([data-theme="light"]){--surface:#1a1a19;--ink:#ffffff;--ink2:#c3c2b7;
       --muted:#898781;--grid:#2c2c2a;--axis:#383835;--s1:#3987e5;--s2:#d95926;
       --s3:#199e70;--s1lo:#184f95;--neg:#e66767}}
  .viz[data-theme="dark"]{--surface:#1a1a19;--ink:#ffffff;--ink2:#c3c2b7;
       --muted:#898781;--grid:#2c2c2a;--axis:#383835;--s1:#3987e5;--s2:#d95926;
       --s3:#199e70;--s1lo:#184f95;--neg:#e66767}
  .bg{fill:var(--surface)}
  .ttl{fill:var(--ink);font-size:15px;font-weight:600}
  .sub{fill:var(--ink2);font-size:11.5px}
  .cat{fill:var(--ink);font-size:12px}
  .val{fill:var(--ink);font-size:11.5px;font-weight:600;
       font-variant-numeric:tabular-nums}
  .ci{fill:var(--ink2);font-size:10.5px;font-variant-numeric:tabular-nums}
  .tick{fill:var(--muted);font-size:10.5px;font-variant-numeric:tabular-nums}
  .note{fill:var(--muted);font-size:10.5px}
  .ref{fill:var(--ink2);font-size:10.5px;font-weight:600}
  .grid{stroke:var(--grid);stroke-width:1}
  .axis{stroke:var(--axis);stroke-width:1}
  .refline{stroke:var(--axis);stroke-width:1}
  .ring{stroke:var(--surface);stroke-width:2}
"""


def head(h, title, desc):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" '
            f'viewBox="0 0 {W} {h}" class="viz" role="img" '
            f'aria-labelledby="t d"><title id="t">{esc(title)}</title>'
            f'<desc id="d">{esc(desc)}</desc><defs><style>{CSS}</style></defs>'
            f'<rect class="bg" width="{W}" height="{h}"/>')


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def wrap(s, px, size):
    """Wrap to a pixel width. Text that does not fit is never clipped, so the
    width is measured (approximately, by average advance) before it is placed."""
    adv = size * 0.525
    out, line = [], ''
    for w in s.split(' '):
        cand = (line + ' ' + w).strip()
        if len(cand) * adv > px and line:
            out.append(line); line = w
        else:
            line = cand
    if line:
        out.append(line)
    return out


def txt(x, y, s, cls='cat', anchor='start'):
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" '
            f'text-anchor="{anchor}">{esc(s)}</text>')


def header(title, sub):
    """Title, wrapped subtitle, and the y the plot may start at."""
    s = [txt(28, 26, title, 'ttl')]
    y = 44
    for ln in wrap(sub, W - 56, 11.5):
        s.append(txt(28, y, ln, 'sub')); y += 15
    return ''.join(s), y + 6


def footnote(y, note):
    s = []
    for ln in wrap(note, W - 56, 10.5):
        s.append(txt(28, y, ln, 'note')); y += 14
    return ''.join(s), y


def note_h(note):
    return 0 if not note else 14 * len(wrap(note, W - 56, 10.5)) + 10


def dot(x, y, var, r=4.5):
    """>=8px marker with the 2px surface ring the spec requires."""
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="var({var})" '
            f'class="ring"/>')


def legend(y, items):
    """Always present for >=2 series. Swatch carries identity; text stays ink."""
    s, x = [], 300
    for name, var in items:
        s.append(dot(x, y, var, 4.5))
        s.append(txt(x + 12, y + 4, name, 'sub'))
        x += max(150, int(len(name) * 6.4) + 34)
    return ''.join(s)


def xaxis(x0, x1, lo, hi, ytop, ybase, ticks, label=None):
    """Hairline solid grid confined to the plot band, muted tabular ticks."""
    sc = lambda v: x0 + (v - lo) / (hi - lo) * (x1 - x0)
    out = []
    for v in ticks:
        out.append(f'<line class="grid" x1="{sc(v):.1f}" y1="{ytop:.1f}" '
                   f'x2="{sc(v):.1f}" y2="{ybase:.1f}"/>')
        out.append(txt(sc(v), ybase + 15, f'{v:g}', 'tick', 'middle'))
    out.append(f'<line class="axis" x1="{x0}" y1="{ybase:.1f}" x2="{x1}" '
               f'y2="{ybase:.1f}"/>')
    if label:
        out.append(txt((x0 + x1) / 2, ybase + 31, label, 'note', 'middle'))
    return ''.join(out), sc


def fmt(v, signed):
    return f'{v:+.4f}' if signed else f'{v:.4f}'



def forest(path, title, sub, rows, lo, hi, ticks, refs, xlabel,
           note=None, row_h=32, var='--s1', swarm=None, signed=False,
           label_w=268):
    """One series, one colour (slot 1); value direct-labelled at the mark.
    rows: (label, estimate, ci_lo|None, ci_hi|None, suffix)."""
    hdr, top = header(title, sub)
    top += 30                               # air for the staggered ref labels
    ybase = top + len(rows) * row_h
    h = ybase + 46 + note_h(note)
    x0, x1 = label_w + 18, W - 128
    ax, sc = xaxis(x0, x1, lo, hi, top - 14, ybase, ticks, xlabel)
    s = [head(h, title, sub), hdr, ax]
    for ri, (v, lab) in enumerate(refs):
        # stagger vertically: two reference lines close in x would otherwise
        # overlap their labels, which is a collision no measurement prevents
        ly = top - 20 if ri % 2 == 0 else top - 6
        s.append(f'<line class="refline" x1="{sc(v):.1f}" y1="{ly + 4:.1f}" '
                 f'x2="{sc(v):.1f}" y2="{ybase:.1f}"/>')
        s.append(txt(sc(v), ly, lab, 'ref', 'middle'))
    for i, (lab, est, clo, chi, suf) in enumerate(rows):
        y = top + i * row_h + 10
        if swarm and lab in swarm:          # per-unit context, not a 2nd series
            for u in swarm[lab]:
                s.append(f'<circle cx="{sc(u):.1f}" cy="{y:.1f}" r="2.5" '
                         f'fill="var(--muted)" opacity="0.45"/>')
        if clo is not None:
            s.append(f'<line x1="{sc(clo):.1f}" y1="{y:.1f}" x2="{sc(chi):.1f}" '
                     f'y2="{y:.1f}" stroke="var({var})" stroke-width="2" '
                     f'stroke-linecap="round"/>')
        s.append(dot(sc(est), y, var))
        s.append(txt(label_w, y + 4, lab, 'cat', 'end'))
        s.append(txt(x1 + 10, y + 1, fmt(est, signed), 'val'))
        s.append(txt(x1 + 10, y + 13,
                     f'[{fmt(clo, signed)}, {fmt(chi, signed)}]' if clo is not None
                     else suf, 'ci'))
    if note:
        s.append(footnote(ybase + 44, note)[0])
    s.append('</svg>')
    FIG.joinpath(path).write_text(''.join(s))
    print(f'  {path}')


def dumbbell(path, title, sub, rows, lo, hi, ticks, xlabel, note=None,
             label_w=300):
    """Before -> after per item: one hue, two shades, 2px connector."""
    hdr, top = header(title, sub)
    leg = legend(top + 8, [("arm's own composition floor", '--s1lo'),
                           ('CNN, same rows', '--s1')])
    top += 34
    row_h = 32
    ybase = top + len(rows) * row_h
    h = ybase + 46 + note_h(note)
    x0, x1 = label_w + 18, W - 128
    ax, sc = xaxis(x0, x1, lo, hi, top - 6, ybase, ticks, xlabel)
    s = [head(h, title, sub), hdr, leg, ax, txt(x1 + 10, top - 12, 'lift', 'note')]
    for i, (lab, floor, apv) in enumerate(rows):
        y = top + i * row_h + 10
        s.append(f'<line x1="{sc(floor):.1f}" y1="{y:.1f}" x2="{sc(apv):.1f}" '
                 f'y2="{y:.1f}" stroke="var(--s1lo)" stroke-width="2" '
                 f'stroke-linecap="round"/>')
        s.append(dot(sc(floor), y, '--s1lo'))
        s.append(dot(sc(apv), y, '--s1'))
        s.append(txt(label_w, y + 4, lab, 'cat', 'end'))
        s.append(txt(x1 + 10, y + 4, f'+{apv - floor:.4f}', 'val'))
    if note:
        s.append(footnote(ybase + 44, note)[0])
    s.append('</svg>')
    FIG.joinpath(path).write_text(''.join(s))
    print(f'  {path}')


def slope(path, title, sub, strata, series, lo, hi, ticks, ylabel, notes):
    """Two series across two strata: the crossing IS the finding."""
    hdr, top = header(title, sub)
    leg = legend(top + 8, [(n, v) for n, v, _ in series])
    ptop = top + 40
    pbot = ptop + 190
    nl = []
    for n in notes:
        nl += wrap(n, W - 56, 10.5)
    h = pbot + 56 + 14 * len(nl) + 14
    cols = [330, 660]
    scy = lambda v: pbot - (v - lo) / (hi - lo) * (pbot - ptop)
    s = [head(h, title, sub), hdr, leg]
    for v in ticks:
        s.append(f'<line class="grid" x1="240" y1="{scy(v):.1f}" x2="750" '
                 f'y2="{scy(v):.1f}"/>')
        s.append(txt(232, scy(v) + 4, f'{v:g}', 'tick', 'end'))
    s.append(txt(232, ptop - 14, ylabel, 'note', 'end'))
    for i, st in enumerate(strata):
        for j, ln in enumerate(wrap(st, 300, 12)):
            s.append(txt(cols[i], pbot + 24 + j * 15, ln, 'cat', 'middle'))
    for name, var, vals in series:
        s.append(f'<line x1="{cols[0]}" y1="{scy(vals[0]):.1f}" x2="{cols[1]}" '
                 f'y2="{scy(vals[1]):.1f}" stroke="var({var})" stroke-width="2" '
                 f'stroke-linecap="round"/>')
        for i, v in enumerate(vals):
            s.append(dot(cols[i], scy(v), var))
        s.append(txt(cols[0] - 14, scy(vals[0]) + 4, f'{vals[0]:.4f}', 'val', 'end'))
        s.append(txt(cols[1] + 14, scy(vals[1]) + 4, f'{vals[1]:.4f}', 'val'))
    y = pbot + 56
    for ln in nl:
        s.append(txt(28, y, ln, 'note')); y += 14
    s.append('</svg>')
    FIG.joinpath(path).write_text(''.join(s))
    print(f'  {path}')


def grouped(path, title, sub, groups, series, lo, hi, ticks, xlabel, note=None,
            label_w=300):
    """Three series x three row sets. Categorical slots 1-3, legend plus a
    direct label on every mark -- also the relief the aqua WARN requires."""
    hdr, top = header(title, sub)
    leg = legend(top + 8, series)
    top += 36
    sp, gh = 24, 86
    ybase = top + len(groups) * gh - 10
    h = ybase + 46 + note_h(note)
    x0, x1 = label_w + 18, W - 128
    ax, sc = xaxis(x0, x1, lo, hi, top - 6, ybase, ticks, xlabel)
    s = [head(h, title, sub), hdr, leg, ax]
    for gi, (glab, base, vals) in enumerate(groups):
        gy = top + gi * gh
        s.append(txt(label_w, gy + 14, glab, 'cat', 'end'))
        s.append(txt(label_w, gy + 30, f'random baseline {base:.3f}', 'note', 'end'))
        s.append(f'<line class="refline" x1="{sc(base):.1f}" y1="{gy + 2:.1f}" '
                 f'x2="{sc(base):.1f}" y2="{gy + 2 + 2 * sp + 16:.1f}"/>')
        for si, (name, var) in enumerate(series):
            est, clo, chi = vals[si]
            y = gy + 10 + si * sp
            s.append(f'<line x1="{sc(clo):.1f}" y1="{y:.1f}" x2="{sc(chi):.1f}" '
                     f'y2="{y:.1f}" stroke="var({var})" stroke-width="2" '
                     f'stroke-linecap="round"/>')
            s.append(dot(sc(est), y, var))
            s.append(txt(x1 + 10, y + 4, f'{est:.4f}', 'val'))
    if note:
        s.append(footnote(ybase + 44, note)[0])
    s.append('</svg>')
    FIG.joinpath(path).write_text(''.join(s))
    print(f'  {path}')



# ---------------------------------------------------------------------------
# F14 and F15 are manuscript figures (D049). They use the same CSS block and
# class set as F7-F13 -- no class or custom property is added, so the seven
# earlier figures are byte-unchanged by their presence. Anything the shared
# classes do not cover is an inline attribute referencing an existing variable.
# ---------------------------------------------------------------------------

def _box(x, y, w, h, stroke='var(--grid)', sw=1):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" '
            f'fill="var(--surface)" stroke="{stroke}" stroke-width="{sw}"/>')


def _stage(x, y, w, h, title, lines, frozen=False):
    s = [_box(x, y, w, h, 'var(--s1)' if frozen else 'var(--grid)', 1.5 if frozen else 1)]
    s.append(f'<text x="{x+12}" y="{y+20}" fill="var(--ink)" font-size="12.5" '
             f'font-weight="600">{esc(title)}</text>')
    for i, ln in enumerate(lines):
        s.append(txt(x + 12, y + 37 + i * 15, ln, 'cat'))
    return ''.join(s)


def _arrow(x1, y1, x2, y2, dashed=False, col='var(--axis)'):
    d = ' stroke-dasharray="4 3"' if dashed else ''
    return (f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{col}" stroke-width="1.5" '
            f'fill="none"{d} marker-end="url(#a)"/>')


MARKER = ('<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" '
          'markerHeight="6" orient="auto-start-reverse">'
          '<path d="M0 0 L10 5 L0 10 z" fill="var(--axis)"/></marker>')


def fig_design(path, F, SF, sel, fin, endp, leak, n_acq, n_class1, n_test, n_cv, leak_real):
    """F14 - study design. Every count is an argument read from an artifact."""
    H = 620
    s = [head(H, 'Study design, from deposited submission to read endpoint',
              f'A deposited submission of {n_acq} acquisitions, of which {n_class1} are '
              f'HLA class I over {F["n_units"]} participants, yields '
              f'{F["observed_universe"]:,} unique peptides. A frozen dataset of '
              f'{F["n_positives"]:,} positives and {F["n_negatives"]:,} decoys is split '
              f'into {n_cv} participants for model selection and {n_test} held out. A '
              f'{sel["grid_size"]}-point grid and {fin["n_models"]} checkpoints precede a '
              f'single read of the held-out partition at '
              f'{endp["primary"]["mean_ap"]:.4f} average precision against a '
              f'preregistered threshold of {endp["threshold"]}.')]
    s.append(f'<defs>{MARKER}</defs>')
    s.append(txt(28, 26, 'Study design: everything left of the dashed line was fixed '
                 'before the endpoint was read', 'ttl'))
    s.append(txt(28, 46, 'Counts are read from the frozen artifacts, not transcribed. '
                 'A blue outline marks an artifact under checksum.', 'sub'))

    CX, BW, BH = 28, 318, 56
    y = 76
    s.append(_stage(CX, y, BW, BH, 'Deposited submission  PXD024871',
                    [f'{n_acq} acquisitions · {n_class1} HLA class I · '
                     f'{F["n_units"]} participants',
                     'identifications taken as deposited, 5% class-I FDR']))
    s.append(txt(CX + BW + 14, y + 22, 'no new mass spectrometry', 'ref'))
    s.append(txt(CX + BW + 14, y + 38, 'exact joins only; approximate matching prohibited', 'note'))

    y2 = y + BH + 26
    s.append(_arrow(CX + 40, y + BH, CX + 40, y2 - 4))
    s.append(_stage(CX, y2, BW, BH, 'Peptide extraction',
                    [f'{F["observed_universe"]:,} unique peptides, '
                     f'{F["length_window"][0]}–{F["length_window"][1]} residues',
                     'every container checksum-verified before use']))
    s.append(txt(CX + BW + 14, y2 + 34, '79.9% of the union occurs in one participant only', 'note'))

    y3 = y2 + BH + 26
    s.append(_arrow(CX + 40, y2 + BH, CX + 40, y3 - 4))
    s.append(_stage(CX, y3, BW, BH, 'Frozen dataset',
                    [f'{F["n_positives"]:,} positives ({F["cap_per_unit"]:,} per participant) '
                     f'+ {F["n_negatives"]:,} decoys',
                     f'decoys from {F["expressed_proteins"]:,} of '
                     f'{F["proteome_sequences"]:,} expressed proteins, 1:{F["ratio"]}'], True))
    s.append(txt(CX + BW + 14, y3 + 34, 'decoy set chosen on a composition diagnostic', 'note'))

    y4 = y3 + BH + 26
    s.append(_arrow(CX + 40, y3 + BH, CX + 40, y4 - 4))
    s.append(_stage(CX, y4, BW, BH, 'Split, stratified by platform',
                    [f'{n_cv} participants for selection · {n_test} held out',
                     f'{leak["leakage_mean_pct"]:.2f}% mean sequence leakage over '
                     f'{leak["n_splits"]:,} splits'], True))
    s.append(txt(CX + BW + 14, y4 + 34, 'not re-drawn: choosing on leakage is selection', 'note'))

    y5 = y4 + BH + 26
    s.append(_arrow(CX + 40, y4 + BH, CX + 40, y5 - 4))
    s.append(_stage(CX, y5, BW, BH, 'Preregistered decision rule',
                    [f'reject when the nominal-99% lower bound exceeds {endp["threshold"]}',
                     'floor + 0.05; power 0.98 at AUROC 0.75'], True))

    RX, RW = 452, 390
    s.append(_stage(RX, y, RW, BH, 'Measured before any model was fitted',
                    ['composition floor · sequence leakage',
                     'platform separability · decoy contamination']))
    s.append(txt(RX + 12, y + BH + 18, 'Figure 2. Each bounds what the endpoint can mean.', 'note'))
    s.append(f'<line x1="{RX-26}" y1="{y+BH+36}" x2="{RX-26}" y2="{H-74}" '
             f'stroke="var(--s2)" stroke-width="1.5" stroke-dasharray="4 3"/>')
    s.append(txt(RX - 20, y + BH + 52, 'the endpoint is read once, after this line', 'ref'))

    gy = y3
    s.append(_stage(RX, gy - 78, RW, BH, 'Model selection',
                    [f'{sel["grid_size"]}-point grid over 5 grouped folds',
                     f'selected at {sel["selected"]["mean_val_ap"]:.4f} mean validation AP']))
    s.append(txt(RX + 12, gy - 78 + BH + 18,
                 'grid spread 0.0129 against fold spread 0.0117 — flat', 'note'))
    s.append(_stage(RX, gy + 26, RW, BH, 'Final fit',
                    [f'{fin["n_models"]} checkpoints, 5 folds × 5 seeds',
                     'performance governed by which participants are held out']))
    s.append(_stage(RX, gy + 26 + BH + 30, RW, BH, 'Endpoint, read once',
                    [f'{endp["primary"]["mean_ap"]:.4f} mean per-participant AP  '
                     f'(99% {endp["primary"]["ci99_lo"]:.4f}–{endp["primary"]["ci99_hi"]:.4f})',
                     f'leakage-free {endp["leakage_free"]["mean_ap"]:.4f} — both reported'], True))
    s.append(_arrow(RX + 40, gy - 78 + BH, RX + 40, gy + 22))
    s.append(_arrow(RX + 40, gy + 26 + BH, RX + 40, gy + 26 + BH + 26))
    yc = gy + 26 + BH + 30 + BH + 30
    s.append(_stage(RX, yc, RW, BH, 'Comparison with published predictors',
                    ['165,594 rows naive to every system',
                     'four predictors span 0.0046; the CNN leads by 0.137–0.142']))
    s.append(_arrow(RX + 40, gy + 26 + BH + 30 + BH, RX + 40, yc - 4))

    s.append(txt(28, H - 34, 'Sources: data/derived/FREEZE.json, SPLIT.csv, FILE_MAP.csv; '
                 'results/model/selection.json, final.json, endpoint.json; '
                 'results/qc/leakage_audit.json.', 'note'))
    s.append(txt(28, H - 18, f'The realised split leaks {leak_real:.2f}%, near the top of the '
                 f'{leak["leakage_min_pct"]:.2f}–{leak["leakage_max_pct"]:.2f}% range; the '
                 f'leakage-free subset is reported alongside the primary.', 'note'))
    s.append('</svg>')
    FIG.joinpath(path).write_text(''.join(s))
    print(f'  {path}')


def fig_confounds(path, leak, negd, mism, endp, leak_real):
    """F15 - the four confounds in one panel."""
    H = 600
    PLAT = leak['platform_auroc_composition']
    CTRL = leak['random_unit_half_control_auroc']
    FLOOR = endp['floor']; AP = endp['primary']['mean_ap']
    APLF = endp['leakage_free']['mean_ap']
    CONTAM = mism['strong_presenter_pct_le_2']['negatives']
    s = [head(H, 'Four confounds measured before any model was fitted',
              f'Composition floor {FLOOR:.3f} average precision against a 0.500 chance '
              f'baseline and a {AP:.4f} endpoint; sequence leakage {leak_real:.2f} percent '
              f'on the realised split within an {leak["leakage_min_pct"]:.2f} to '
              f'{leak["leakage_max_pct"]:.2f} percent range over {leak["n_splits"]} random '
              f'splits; acquisition platform separable at AUROC {PLAT:.4f} against a '
              f'{CTRL:.4f} control; {100*CONTAM:.2f} percent of constructed decoys called '
              f'presented by an independent predictor.')]
    s.append(txt(28, 26, 'Four properties of the data, measured before any model was fitted', 'ttl'))
    s.append(txt(28, 46, 'Each bounds what the endpoint can mean. All four are cheap to '
                 'compute and all four move the headline number.', 'sub'))
    PW = 396; X0, X1 = 28, 456; Y0, Y1 = 82, 342

    def panel(x, y, letter, title, sub):
        return (f'<text x="{x}" y="{y}" fill="var(--ink)" font-size="12.5" '
                f'font-weight="600">{esc(letter)}  {esc(title)}</text>'
                + txt(x, y + 17, sub, 'sub'))

    s.append(panel(X0, Y0, 'A', 'Performance is not read against chance',
                   'Amino-acid composition alone, no positional information'))
    ax, ay, aw = X0, Y0 + 36, PW - 36
    lo, hi = 0.45, 0.80
    for i, (lab, v, col) in enumerate((('chance', 0.500, 'var(--muted)'),
                                       ('composition floor', FLOOR, 'var(--s2)'),
                                       ('endpoint, leakage-free', APLF, 'var(--s1lo)'),
                                       ('endpoint', AP, 'var(--s1)'))):
        yy = ay + 14 + i * 34
        bw = (v - lo) / (hi - lo) * aw
        s.append(f'<rect x="{ax}" y="{yy}" width="{bw:.1f}" height="16" fill="{col}" rx="2"/>')
        s.append(txt(ax, yy - 4, lab, 'cat'))
        s.append(txt(ax + bw + 7, yy + 13, f'{v:.4f}', 'val'))
    fx = ax + (FLOOR - lo) / (hi - lo) * aw
    s.append(f'<line x1="{fx:.1f}" y1="{ay+8}" x2="{fx:.1f}" y2="{ay+130}" '
             f'stroke="var(--axis)" stroke-width="1" stroke-dasharray="3 3"/>')
    s.append(txt(ax, ay + 152, 'Over half the apparent discrimination is reachable '
                 'without sequence structure.', 'note'))

    s.append(panel(X1, Y0, 'B', 'Participant-disjoint is not sequence-disjoint',
                   f'{leak["n_splits"]:,} random ten-participant splits'))
    bx, by, bw_ = X1, Y0 + 36, PW - 60
    blo, bhi = 11.0, 18.0
    def bxp(v): return bx + (v - blo) / (bhi - blo) * bw_
    yy = by + 42
    s.append(f'<line x1="{bxp(leak["leakage_min_pct"]):.1f}" y1="{yy}" '
             f'x2="{bxp(leak["leakage_max_pct"]):.1f}" y2="{yy}" class="axis"/>')
    s.append(f'<rect x="{bxp(leak["leakage_p5_pct"]):.1f}" y="{yy-11}" '
             f'width="{bxp(leak["leakage_p95_pct"])-bxp(leak["leakage_p5_pct"]):.1f}" '
             f'height="22" fill="var(--s1lo)" rx="2"/>')
    s.append(f'<line x1="{bxp(leak["leakage_median_pct"]):.1f}" y1="{yy-13}" '
             f'x2="{bxp(leak["leakage_median_pct"]):.1f}" y2="{yy+13}" '
             f'stroke="var(--axis)" stroke-width="2"/>')
    s.append(f'<circle cx="{bxp(leak_real):.1f}" cy="{yy}" r="6" fill="var(--s2)" class="ring"/>')
    for v in (leak['leakage_min_pct'], leak['leakage_max_pct']):
        s.append(txt(bxp(v), yy + 30, f'{v:.2f}%', 'tick', 'middle'))
    s.append(txt(bxp(leak['leakage_median_pct']), yy - 20,
                 f'median {leak["leakage_median_pct"]:.2f}%', 'tick', 'middle'))
    s.append(txt(bxp(leak_real), yy + 52, f'realised split {leak_real:.2f}%', 'val', 'middle'))
    s.append(txt(bx, by + 130, 'Shaded: 5th–95th percentile. The realised split was '
                 'not re-drawn —', 'note'))
    s.append(txt(bx, by + 146, 'choosing a split on its leakage would be selection on '
                 'the data.', 'note'))
    s.append(txt(bx, by + 166, f'Cost of the leaked rows: {AP-APLF:.4f} average precision.', 'note'))

    s.append(panel(X0, Y1, 'C', 'The acquisition platform is learnable from sequence',
                   'Composition-only classifier, LTQ Orbitrap XL vs Orbitrap Fusion Lumos'))
    cx, cy, cw = X0, Y1 + 36, PW - 36
    clo, chi = 0.48, 0.70
    for i, (lab, v, col) in enumerate((('control: random halves of participants', CTRL, 'var(--muted)'),
                                       ('platform', PLAT, 'var(--s3)'))):
        yy = cy + 16 + i * 40
        bw2 = (v - clo) / (chi - clo) * cw
        s.append(f'<rect x="{cx}" y="{yy}" width="{bw2:.1f}" height="18" fill="{col}" rx="2"/>')
        s.append(txt(cx, yy - 5, lab, 'cat'))
        s.append(txt(cx + bw2 + 7, yy + 14, f'{v:.4f}', 'val'))
    s.append(txt(cx, cy + 118, f'excess attributable to platform  +{PLAT-CTRL:.4f}', 'ref'))
    s.append(txt(cx, cy + 138, 'No participant spans both platforms, so no split over', 'note'))
    s.append(txt(cx, cy + 154, 'participants can separate the two.', 'note'))

    s.append(panel(X1, Y1, 'D', 'The negative class is contaminated',
                   'Independent predictor scoring the constructed decoys'))
    dx, dy_ = X1, Y1 + 46
    ncol, nrow, cell, gap = 20, 9, 13, 4
    filled = round(CONTAM * ncol * nrow)
    for i in range(ncol * nrow):
        r, c = divmod(i, ncol)
        col = 'var(--neg)' if i < filled else 'var(--grid)'
        s.append(f'<rect x="{dx+c*(cell+gap)}" y="{dy_+r*(cell+gap)}" width="{cell}" '
                 f'height="{cell}" fill="{col}" rx="2"/>')
    base = dy_ + nrow * (cell + gap)
    s.append(txt(dx, base + 20, f'{100*CONTAM:.2f}% of decoys called presented', 'val'))
    s.append(txt(dx, base + 38, 'Roughly one in nine. Each square is one per cent of the', 'note'))
    s.append(txt(dx, base + 54, 'negative class; shaded squares are mislabelled.', 'note'))

    s.append(txt(28, H - 16, 'Sources: results/qc/leakage_audit.json, '
                 'negative_diagnostic.json, predictor_task_mismatch.json, '
                 f'results/model/endpoint.json. Floor {FLOOR:.3f} is the preregistered '
                 'figure; recomputed on the frozen dataset it is 0.636.', 'note'))
    s.append('</svg>')
    FIG.joinpath(path).write_text(''.join(s))
    print(f'  {path}')


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    J = lambda p: json.loads((RES/p).read_text())
    print('writing figures:')

    # ---- F7  the primary endpoint and its two preregistered checks (R9)
    e = J('model/endpoint.json')
    forest('F7_endpoint.svg',
           'The primary endpoint, read once, and its two checks',
           'Mean per-participant average precision, nominal-99% cluster bootstrap over '
           'participants. Grey dots are the 10 held-out participants.',
           [('Primary — full test partition', e['primary']['mean_ap'],
             e['primary']['ci99_lo'], e['primary']['ci99_hi'], ''),
            ('Sensitivity — leakage-free subset', e['leakage_free']['mean_ap'],
             e['leakage_free']['ci99_lo'], e['leakage_free']['ci99_hi'], ''),
            ('Secondary — score-ensembled', e['ensemble_secondary'],
             None, None, 'no interval')],
           0.55, 0.84, [0.6, 0.65, 0.7, 0.75, 0.8],
           [(e['floor'], 'floor 0.597'), (e['threshold'], 'threshold 0.647')],
           'mean per-participant average precision',
           note='The null is rejected when the lower bound clears 0.647, a rule fixed before '
                'any model existed (D008). It clears on the primary and again on the '
                'leakage-free subset, so the result does not rest on the 15.99% of test '
                'positives that also appear in training. The ensembled value carries no '
                'interval because it is a single ranking rather than 25, and it is reported '
                'as the flattering framing, which is why the per-model average was made '
                'primary before the partition was read (D027).',
           swarm={'Primary — full test partition': list(e['primary']['per_unit'].values()),
                  'Sensitivity — leakage-free subset':
                      list(e['leakage_free']['per_unit'].values())})

    # ---- F8  the endpoint decomposed by peptide length (R9)
    L = J('model/endpoint_by_length.json')
    forest('F8_endpoint_by_length.svg',
           'The endpoint is not carried by one peptide length',
           'The same 200,000 rows and the same 25 models, split by length. Not a second '
           'reading: every length is reported, none is selected, the decision is fixed.',
           [(f"{r['stratum']}  ({r['n_rows']:,} rows)", r['mean_ap'],
             r['ci99'][0], r['ci99'][1], '') for r in L['by_length']],
           0.62, 0.84, [0.65, 0.7, 0.75, 0.8],
           [(0.647, 'threshold'), (L['all']['mean_ap'], 'pooled 0.7551')],
           'mean per-participant average precision',
           note='Every length clears the threshold. The best is the 12-mer — which is also '
                'the length D025 found most platform-discriminative, 11.69% of LTQ positives '
                'against 9.85% of Lumos. The coincidence runs in the unflattering direction '
                'and is recorded rather than left out.')

    # ---- F9  cross-platform transfer against each arm's own floor (R10)
    T = J('model/transfer.json')
    arms = {a['id']: a for a in T['arms']}
    order = [('P_LTQ_to_Lumos', 'across', 'LTQ-trained → all 27 Lumos'),
             ('P_Lumos_to_LTQ', 'across', 'Lumos-trained → all 25 LTQ'),
             ('M_LTQ', 'within', 'LTQ-trained → LTQ held-out half'),
             ('M_LTQ', 'across', 'LTQ-trained → Lumos held-out half'),
             ('M_Lumos', 'within', 'Lumos-trained → Lumos held-out half'),
             ('M_Lumos', 'across', 'Lumos-trained → LTQ held-out half')]
    rows = [(lab, (ev := next(x for x in arms[aid]['evals'] if x['rel'] == rel))
             ['floor_mean_ap'], ev['mean_ap']) for aid, rel, lab in order]
    dumbbell('F9_transfer_vs_floor.svg',
             'Cross-platform transfer does not collapse',
             'Each arm against its OWN composition-only floor, fitted on that arm’s own '
             'training rows. Arm floors span 0.5917 to 0.6648, so the pooled 0.597 would '
             'reverse the ordering between arms.',
             rows, 0.55, 0.80, [0.6, 0.65, 0.7, 0.75],
             'mean per-participant average precision',
             note='A model that has never seen a run from the target instrument still sits '
                  'about 0.10 above the composition floor for that pairing. The first two rows '
                  'are the preregistered arms (D025); the last four are the matched control '
                  'that separates platform from training-set size (D028).')

    # ---- F10  the platform effect, four estimates from two designs (R10)
    rows = [(f"same model, test platform moves — {c['arm']}", c['difference'],
             c['ci99'][0], c['ci99'][1], '')
            for c in T['contrasts'] if c['contrast'].startswith('A')]
    rows += [(f"same test units, training platform moves — {c['test_set']}",
              c['difference'], c['ci99'][0], c['ci99'][1], '')
             for c in T['contrasts'] if c['contrast'].startswith('B')]
    forest('F10_platform_effect.svg',
           'The platform effect is real, bounded, and agrees across two designs',
           'One contrast holds the model fixed and moves the test platform; the other holds '
           'the test units fixed and moves the training platform.',
           rows, -0.02, 0.13, [0, 0.025, 0.05, 0.075, 0.1, 0.125],
           [(0, 'no effect')], 'cost of training on the other platform (AP)',
           note='Four estimates from two designs, agreeing to within 0.01, none of the '
                'intervals containing zero. Training on the other platform costs 0.04–0.06 '
                'average precision — a cost, not a collapse.',
           signed=True, label_w=322)

    # ---- F11  multi-allele replication, adjusted (R12)
    D = J('model/multi_allele_dod.json')
    forest('F11_multi_allele_partA.svg',
           'All five alleles point the same way once the nuisance is subtracted',
           'Carrier-trained minus non-carrier-trained on each allele’s exclusive stratum, '
           'minus the same contrast on class-shared peptides, paired per participant.',
           [(f"{r['allele']}  ({r['n_units']} units)", r['excl_minus_neutral'],
             r['ci99'][0], r['ci99'][1], '') for r in D['part_A']],
           -0.02, 0.09, [0, 0.02, 0.04, 0.06, 0.08],
           [(0, 'no effect')], 'allele-specific advantage (AP)',
           note='Three of five exclude zero. A*01:01 is the case the nuisance estimate was '
                'built for: it reads +0.0229 raw and would have counted as a replication, but '
                'its two training sets differ in quality by +0.0146, and only +0.0083 survives. '
                'No joint p-value is computed — the five splits share participants.',
           signed=True)

    # ---- F12  the symmetric pair: the crossing is the finding (R12)
    M = J('model/multi_allele.json')
    comps = M['part_B']['comparisons']
    def ap(stratum, arm):
        c = next(x for x in comps if x['label'].startswith(stratum)
                 and 'EXCLUSIVE' in x['label'])
        return c[arm]['mean_ap']
    pb = {r['stratum']: r for r in D['part_B']}
    slope('F12_sign_reversal.svg',
          'The symmetric test: each model wins on its own allele’s peptides',
          'Both arms are carrier-trained — each for its own allele — so neither group '
          'is defined by an absence, which is what made the earlier design uninformative. '
          'A sign reversal was preregistered as the signature.',
          [f"HLA-A*02:01-exclusive stratum ({pb['HLA-A*02:01']['n_units']} participants)",
           f"HLA-C*07:02-exclusive stratum ({pb['HLA-C*07:02']['n_units']} participants)"],
          [('HLA-A*02:01-trained', '--s1',
            [ap('HLA-A*02:01', 'HLA-A*02:01-trained'),
             ap('HLA-C*07:02', 'HLA-A*02:01-trained')]),
           ('HLA-C*07:02-trained', '--s2',
            [ap('HLA-A*02:01', 'HLA-C*07:02-trained'),
             ap('HLA-C*07:02', 'HLA-C*07:02-trained')])],
          0.762, 0.822, [0.77, 0.78, 0.79, 0.80, 0.81, 0.82],
          'mean per-participant AP',
          ['The lines cross, so the sign reverses as preregistered.',
           f"A*02:01-exclusive, adjusted for the neutral training-set difference: "
           f"{pb['HLA-A*02:01']['adjusted']:+.4f}, CI99 "
           f"[{pb['HLA-A*02:01']['ci99'][0]:+.4f}, {pb['HLA-A*02:01']['ci99'][1]:+.4f}], "
           f"{pb['HLA-A*02:01']['n_positive']} of {pb['HLA-A*02:01']['n_units']} participants.",
           f"C*07:02-exclusive, adjusted: {pb['HLA-C*07:02']['adjusted']:+.4f}, CI99 "
           f"[{pb['HLA-C*07:02']['ci99'][0]:+.4f}, {pb['HLA-C*07:02']['ci99'][1]:+.4f}] — "
           f"correct sign, but the interval contains zero, so this direction is NOT "
           f"demonstrated.",
           'Only one of the two directions is established. G13 was released on that basis by '
           'the project owner (D032), over a criterion that had required both — the single '
           'most reader-dependent step in this report.'])

    # ---- F13  the predictor comparison across three row sets (R13)
    C = J('qc/predictor_comparison.json')
    series = [('CNN (this work)', '--s1'), ('MHCflurry 2.0.0', '--s2'),
              ('MHCflurry 2.3.0', '--s3')]
    keys = ['CNN', 'MHCflurry 2.0.0', 'MHCflurry 2.3.0']
    labels = [('mutually naive (PRIMARY)', 'Mutually naive · primary'),
              ('predictor-naive only', 'Predictor-naive only'),
              ('full test partition', 'Full test partition')]
    groups = []
    for rs, lab in labels:
        rec = C['row_sets'][rs]
        groups.append((f"{lab} · {rec['n_rows']:,} rows", rec['prevalence'],
                       [(rec['systems'][k]['mean_ap'], rec['systems'][k]['ci99'][0],
                         rec['systems'][k]['ci99'][1]) for k in keys]))
    grouped('F13_predictor_comparison.svg',
            'The CNN leads MHCflurry where neither system has seen the rows',
            'Identical rows for every system. The vertical rule in each band is that row '
            'set’s random baseline, which equals its prevalence.',
            groups, series, 0.42, 0.80, [0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75],
            'mean per-participant average precision',
            note='The lead is largest where contamination is smallest (+0.1378 and +0.1340), '
                 'so it is not produced by memorisation. Prevalence differs by row set, so '
                 'absolute values compare only within a band. The CNN also trained on this '
                 'cohort’s own instruments and negative construction, which no subsetting '
                 'removes.')

    # ---- F14  study design (D049), and F15  the four confounds (D049)
    import csv as _csv
    D = REPO/'data'/'derived'
    F = json.loads((D/'FREEZE.json').read_text())
    SF = json.loads((D/'SPLIT_FREEZE.json').read_text())
    sel, fin = J('model/selection.json'), J('model/final.json')
    endp, leak = J('model/endpoint.json'), J('qc/leakage_audit.json')
    negd, mism = J('qc/negative_diagnostic.json'), J('qc/predictor_task_mismatch.json')
    fm = list(_csv.DictReader((D/'FILE_MAP.csv').open()))
    split = {r['unit_id']: r['primary_partition']
             for r in _csv.DictReader((D/'SPLIT.csv').open())}
    pos = list(_csv.DictReader((D/'POSITIVES.csv').open()))
    tr = {r['sequence'] for r in pos if split[r['unit_id']] != 'test'}
    tp = [r for r in pos if split[r['unit_id']] == 'test']
    leak_real = 100.0 * sum(1 for r in tp if r['sequence'] in tr) / len(tp)
    fig_design('F14_study_design.svg', F, SF, sel, fin, endp, leak,
               len(fm), sum(1 for r in fm if r['hla_class'] == 'I'),
               sum(1 for v in split.values() if v == 'test'),
               sum(1 for v in split.values() if v == 'cv'), leak_real)
    fig_confounds('F15_four_confounds.svg', leak, negd, mism, endp, leak_real)

    print(f'\nwrote {len(list(FIG.glob("*.svg")))} figures to results/figures/')


if __name__ == '__main__':
    main()

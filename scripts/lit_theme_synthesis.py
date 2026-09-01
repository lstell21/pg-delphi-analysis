#!/usr/bin/env python3
"""
Thematic coverage of the reviewed literature.

Determines which of the eight themes each included publication addresses, over
the corpus the review reports, and emits the summary table plus a per-publication
assignment for the supplement.

Method. Coverage is decided by matching a stated term list against each
publication's extracted challenge and recommendation text. Those fields are
bullet lists of claims, so a term occurring there is already situated in an
assertion about that topic rather than in passing narration, which is what makes
matching viable here and would not make it viable against full text.

Why deterministic rather than a model pass. The original synthesis was a single
undocumented call and could not be reproduced, which is the gap this replaces. A
term list is auditable, re-runnable, and can be *validated*: hand-label a random
subsample and measure agreement (--sample-for-labelling, then --validate). A
model pass cannot be validated without the same hand-labelling, so it would cost
more and prove less. The term lists below are therefore the codebook, published
in the appendix, and every assignment is emitted with the terms that triggered it
so any single call can be checked or overruled.

Do not tune the term lists to reproduce the original percentages. Those came from
the unreproducible pass and are not ground truth; the hand-labelled subsample is.

Usage:
    python scripts/lit_theme_synthesis.py --run <screen.csv>
    python scripts/lit_theme_synthesis.py --run <screen.csv> --audit
    python scripts/lit_theme_synthesis.py --run <screen.csv> --sample-for-labelling 30
    python scripts/lit_theme_synthesis.py --run <screen.csv> --validate labels.csv
"""

import argparse
import collections
import csv
import random
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIRS = [
    PROJECT_ROOT / "tables",
]

COL_KEY = "Key"
COL_TITLE = "Title"
COL_DECISION = "Decision"
COL_STATUS = "Status"
TEXT_COLS = ["Challenges", "Recommendations"]

# A publication counts as addressing a theme on one matched term. Two was tried
# and left 46% of the corpus unassigned: the extractions are terse (median ~900
# characters), so a theme is typically named once even when squarely addressed.
MIN_HITS = 1

# ── Codebook ──────────────────────────────────────────────────────────────────
# Every theme label names more than one concept, so terms are grouped by the
# component they serve. This is not cosmetic: it makes an unserved component
# visible. The first version had one flat list per theme, and the documentation
# half of "reporting standards and documentation" was carried by a single
# pattern that matched nothing, which is invisible in a flat list and obvious
# here. `--audit` reports coverage per component for the same reason.
#
# Terms are regular expressions matched case-insensitively against the challenge
# and recommendation text. Themes are multi-label: a bullet may legitimately
# support several, so shares sum past 100.

THEMES = [
    ("data_governance", "Data governance, sharing, and infrastructure", [
        ("governance", [r"data govern", r"privacy", r"data protection", r"data use agreement",
                        r"consent", r"ethical[^.]{0,20}data"]),
        ("sharing", [r"data shar", r"data access", r"data availab", r"open data", r"\bFAIR\b",
                     r"data linkage", r"linked data"]),
        # "surveillance data" occurs in almost any epidemiology paper, so the
        # bare noun was dropped: the theme needs the system, not the substance.
        # "repositor" likewise fired on a transparency paper's code repository.
        ("infrastructure", [r"data infrastructure", r"surveillance (system|platform|network)",
                            r"real-?time data", r"interoperab", r"data pipeline",
                            r"data (registry|repositor)", r"routine data", r"health data",
                            r"data collection", r"data quality", r"data standard"]),
    ]),
    ("uncertainty", "Uncertainty quantification and communication", [
        # identifiability, stochasticity, and sensitivity analysis were moved to
        # model development: hand-labelling showed they fire on fitting and
        # estimation problems, not on claims about uncertainty. "robustness" was
        # dropped as too vague to attribute.
        ("quantification", [r"uncertaint", r"confidence interval", r"credible interval",
                            r"probabilistic", r"prediction interval",
                            r"structural uncertainty", r"parameter uncertainty",
                            r"\bbias(es)?\b[^.]{0,25}(estimat|inference)"]),
        ("communication of uncertainty",
         [r"communicat\w*[^.]{0,30}uncertaint", r"convey\w*[^.]{0,25}uncertaint",
          r"uncertaint\w*[^.]{0,30}communicat"]),
    ]),
    ("public_comm", "Public and stakeholder communication", [
        ("public", [r"public communicat", r"communicat\w*[^.]{0,30}public", r"\bmedia\b",
                    r"public trust", r"public understanding", r"misinformation",
                    r"lay (audience|public|reader)", r"general public", r"public perception"]),
        ("stakeholder", [r"stakeholder", r"end-?user[^.]{0,30}(engag|communicat|need)",
                         r"engag\w*[^.]{0,25}(public|communit|stakeholder)",
                         r"co-?produc", r"co-?develop"]),
        ("presentation", [r"visuali[sz]ation", r"plain language", r"interactive (tool|dashboard)",
                          r"communicat\w*[^.]{0,40}(non-?technical|non-?expert)"]),
    ]),
    ("sci_policy", "Science-policy interface", [
        ("actors", [r"policy\s?maker", r"decision\s?maker", r"health agenc",
                    r"public health authorit", r"\bend-?user"]),
        ("interface", [r"science-?policy", r"advisory", r"decision support", r"policy impact",
                       r"policy process", r"translat\w*[^.]{0,25}polic", r"operational need",
                       r"inform\w*[^.]{0,25}(decision|polic)", r"actionab"]),
    ]),
    ("model_dev", "Model development and methodological improvement", [
        # "model structure" is deliberately absent: it matched "decision-makers unable
        # to decipher model structure", which is transparency.
        ("model choice", [r"model complexity", r"model selection", r"hybrid model",
                          r"agent-?based", r"compartmental", r"individual-?based",
                          r"\bIBM\b", r"machine learning", r"fit for purpose",
                          r"choice of model", r"homogeneous mixing",
                          r"oversimplified assumption", r"structural model"]),
        # Fitting and estimation. `parameteri[sz]` required an "e" and so missed
        # "overparametrization"; hand-labelling surfaced 12 such misses.
        ("methodological improvement",
         [r"calibrat", r"parametri[sz]", r"parameter estimation", r"model fitting",
          r"\bMCMC\b", r"identifiabilit", r"sensitivity analys", r"stochastic",
          r"model criticism", r"ensemble", r"multi-?model", r"model validation",
          r"model comparison", r"methodolog\w*[^.]{0,25}(improve|advance|develop)"]),
    ]),
    ("capacity_equity", "Capacity building and global equity", [
        # Bare "training" is excluded: in this corpus it matches "training data" and
        # "annotated training data" as often as workforce training.
        ("capacity building",
         [r"capacity[^.]{0,25}(build|develop|strengthen|constrain)", r"local capacity",
          r"workforce", r"training(?![- ]?(data|set))", r"curricul", r"fellowship",
          r"sustained funding", r"\bskills\b"]),
        # Hand-labelling showed the corpus names the global gap concretely
        # ("developing countries", "outside USA/China", "esp. Africa") more often
        # than by the abstract vocabulary the first list assumed.
        ("global equity", [r"low-?\s?and middle-?income", r"\bLMIC", r"global (south|equity)",
                           r"equity", r"inequalit", r"resource-?(limited|constrained|poor)",
                           r"under-?resourced", r"north-?south", r"vulnerable population",
                           r"developing countr", r"\bAfrica", r"underrepresent",
                           r"geographic\w*[^.]{0,25}(bias|coverage|representat|disparit)"]),
    ]),
    ("transparency", "Model transparency and reproducibility", [
        ("transparency", [r"transparen", r"black box", r"decipher model",
                          r"assumptions[^.]{0,30}(explicit|stated|document|clear)",
                          r"opaque"]),
        # The corpus writes "publish model code and documentation", never "code
        # availability", so the earlier availability-phrased patterns never fired.
        # Bare \bcode\b over-fired on data and pipeline talk; the theme is about
        # model code being inspectable, so the term now needs that context.
        ("reproducibility", [r"reproducib\w*[^.]{0,25}model", r"model[^.]{0,25}reproducib",
                             r"replicat\w*[^.]{0,25}(model|result|analys)", r"open science",
                             r"open source", r"model code", r"code (and|/)\s?documentation",
                             r"publish\w*[^.]{0,20}code", r"open code", r"version control",
                             r"auditab", r"re-?run"]),
    ]),
    ("reporting", "Reporting standards and documentation", [
        ("reporting standards",
         [r"reporting (standard|guideline|item|checklist|practice)", r"checklist",
          r"EPIFORGE", r"CHEERS", r"minimum reporting", r"standardi[sz]ed reporting",
          r"\bODD protocol", r"reporting[^.]{0,25}(consisten|complete)"]),
        ("documentation",
         [r"documentation", r"document\w*[^.]{0,30}(method|assumption|parameter|data source|model)",
          r"metadata", r"\bprovenance\b", r"model description"]),
    ]),
]
THEME_KEYS = [t[0] for t in THEMES]
THEME_LABEL = {k: l for k, l, _ in THEMES}


def terms_of(theme_entry) -> list:
    """Flatten a theme's component groups into one term list."""
    return [t for _component, terms in theme_entry[2] for t in terms]


def tex_escape(s: str) -> str:
    # Backslash first, or the replacements below would be re-escaped. Without it
    # a pattern like \bFAIR\b emits \texttt{\bFAIR\b}, and \b is a LaTeX accent
    # command, so the table fails to typeset.
    s = s.replace("\\", r"\textbackslash{}")
    repl = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
            "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    for k, v in repl.items():
        s = s.replace(k, v)
    return s


def readable_term(pattern: str) -> str:
    """Render a codebook regex as something a reader can check.

    The published table has to be auditable by someone who does not read regular
    expressions, so implementation detail is dropped and the matching intent is
    kept: word boundaries disappear, alternations become slashes, and a bounded
    "any characters" gap becomes an ellipsis meaning "near, within a sentence".
    The exact patterns remain in the deposited script, which is what actually runs.
    """
    s = pattern

    # Negative lookahead is the only construct that changes meaning rather than
    # merely constraining it, so it is spelled out rather than dropped.
    excl = re.search(r"\(\?\!([^)]*(?:\)[^)]*)*)\)", s)
    note = ""
    if excl:
        inner = re.sub(r"[\[\]()?\\]", "", excl.group(1))
        # Character classes like [- ] leave stray separators on each alternative.
        alts = [a.strip(" -_") for a in inner.split("|")]
        note = " (but not " + " / ".join(a for a in alts if a) + ")"
        s = s[:excl.start()] + s[excl.end():]

    s = s.replace(r"\b", "")                                # word boundaries
    s = re.sub(r"\[\^\.\]\{0,\d+\}", " ... ", s)            # bounded proximity
    s = s.replace(r"\w*", "").replace(r"\s?", " ")
    s = re.sub(r"\[sz\]", "s/z", s)                         # British/US spelling
    s = re.sub(r"\(([^()]*)\)", lambda m: m.group(1).replace("|", " / "), s)
    s = s.replace("-?", "-").replace("?", "")
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s + note


def load(run: Path):
    with run.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows, fields = list(reader), (reader.fieldnames or [])
    missing = [c for c in [COL_TITLE, COL_DECISION, COL_STATUS] + TEXT_COLS if c not in fields]
    if missing:
        raise SystemExit("error: missing columns: " + ", ".join(missing))
    return [r for r in rows
            if (r.get(COL_STATUS) or "").strip().lower() == "ok"
            and (r.get(COL_DECISION) or "").strip().lower() == "include"]


def text_of(rec) -> str:
    return " \n ".join((rec.get(c) or "") for c in TEXT_COLS)


def assign(rec) -> dict:
    """{theme_key: [matched terms]} for one publication."""
    text = text_of(rec)
    out = {}
    for entry in THEMES:
        key = entry[0]
        hits = sorted({t for t in terms_of(entry) if re.search(t, text, re.I)})
        if len(hits) >= MIN_HITS:
            out[key] = hits
    return out


def ident_of(rec) -> str:
    return (rec.get(COL_KEY) or rec.get(COL_TITLE) or "").strip()


# ── Validation ────────────────────────────────────────────────────────────────

def sample_for_labelling(recs, n, seed, path: Path, exclude: list = None):
    """Draw n publications at random, optionally excluding earlier samples.

    Without --exclude, a second draw overlaps the first by chance, which
    quietly contaminates a held-out set: the codebook was tuned on the earlier
    sample, so shared rows are no longer held out however the labelling was done.
    """
    seen = set()
    for path_prev in (exclude or []):
        with Path(path_prev).open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                ident = (row.get(COL_KEY) or row.get(COL_TITLE) or "").strip()
                if ident:
                    seen.add(ident)
    pool = [r for r in recs if ident_of(r) not in seen]
    if seen:
        print(f"  excluding {len(seen)} previously sampled, {len(pool)} remain")
    if len(pool) < n:
        raise SystemExit(f"error: only {len(pool)} publications left after exclusions")
    rng = random.Random(seed)
    picked = rng.sample(pool, min(n, len(pool)))
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([COL_KEY, COL_TITLE, "extracted_text"] + THEME_KEYS)
        for r in picked:
            w.writerow([r.get(COL_KEY, ""), r.get(COL_TITLE, ""), text_of(r)]
                       + [""] * len(THEME_KEYS))
    print(f"  wrote {path}")
    print(f"  {len(picked)} publications, seed {seed}. Put 1 or 0 in each theme column,")
    print(f"  judging only from the extracted text, then run --validate on the file.")


def validate(recs, labels_path: Path):
    truth = {}
    with labels_path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            ident = (row.get(COL_KEY) or row.get(COL_TITLE) or "").strip()
            vals = {}
            for k in THEME_KEYS:
                raw = (row.get(k) or "").strip().lower()
                if raw not in {"0", "1", "true", "false", "yes", "no", "y", "n"}:
                    raise SystemExit(f"error: {ident!r} column {k!r} is {raw!r}; "
                                     f"every cell must be labelled 0 or 1")
                vals[k] = raw in {"1", "true", "yes", "y"}
            truth[ident] = vals
    if not truth:
        raise SystemExit("error: no labelled rows found")

    by_ident = {ident_of(r): r for r in recs}
    stats = {k: collections.Counter() for k in THEME_KEYS}
    for ident, gold in truth.items():
        if ident not in by_ident:
            raise SystemExit(f"error: labelled publication not in the run: {ident!r}")
        pred = set(assign(by_ident[ident]))
        for k in THEME_KEYS:
            g, p = gold[k], k in pred
            stats[k]["tp" if (g and p) else "fp" if p else "fn" if g else "tn"] += 1

    print(f"  validated against {len(truth)} hand-labelled publications\n")
    print(f"    {'theme':<46} {'prec':>5} {'rec':>5} {'F1':>5}   tp  fp  fn")
    tot = collections.Counter()
    f1s = []
    for k in THEME_KEYS:
        s = stats[k]
        tot.update(s)
        prec = s["tp"] / (s["tp"] + s["fp"]) if s["tp"] + s["fp"] else float("nan")
        rec = s["tp"] / (s["tp"] + s["fn"]) if s["tp"] + s["fn"] else float("nan")
        f1 = (2 * prec * rec / (prec + rec)) if prec == prec and rec == rec and prec + rec else float("nan")
        if f1 == f1:
            f1s.append(f1)
        print(f"    {THEME_LABEL[k]:<46} {prec:5.2f} {rec:5.2f} {f1:5.2f}  "
              f"{s['tp']:3d} {s['fp']:3d} {s['fn']:3d}")
    mp = tot["tp"] / (tot["tp"] + tot["fp"]) if tot["tp"] + tot["fp"] else float("nan")
    mr = tot["tp"] / (tot["tp"] + tot["fn"]) if tot["tp"] + tot["fn"] else float("nan")
    mf = 2 * mp * mr / (mp + mr) if mp + mr else float("nan")
    n_dec = sum(tot.values())
    acc = (tot["tp"] + tot["tn"]) / n_dec

    # Cohen's kappa: raw agreement flatters a task where most cells are
    # negative, so report the chance-corrected figure alongside it.
    p_yes = ((tot["tp"] + tot["fn"]) / n_dec) * ((tot["tp"] + tot["fp"]) / n_dec)
    p_no = ((tot["tn"] + tot["fp"]) / n_dec) * ((tot["tn"] + tot["fn"]) / n_dec)
    pe = p_yes + p_no
    kappa = (acc - pe) / (1 - pe) if pe < 1 else float("nan")

    print(f"\n    micro-averaged      precision {mp:.2f}  recall {mr:.2f}  F1 {mf:.2f}")
    if f1s:
        print(f"    macro-averaged F1   {sum(f1s) / len(f1s):.2f}")
    print(f"    raw agreement       {acc:.2f} over {n_dec} publication-theme decisions")
    print(f"    Cohen's kappa       {kappa:.2f}  (chance agreement {pe:.2f})")


# ── Output ────────────────────────────────────────────────────────────────────

def build_table(counts, n) -> str:
    ordered = sorted(THEMES, key=lambda t: -counts.get(t[0], 0))
    L = ["% Auto-generated by scripts/lit_theme_synthesis.py -- do not edit by hand.",
         r"\begin{table}[!htbp]", r"\centering",
         rf"\caption{{\textbf{{Theme coverage across the reviewed literature.}} Coverage of "rf"the eight themes across the {n} included publications. A "
         rf"publication counts as addressing a theme where the challenge and recommendation "
         rf"text extracted from it matches a term from that theme's list, given in "
         rf"\protect\hyperref[sec:app:coding]{{Supplementary Note 16}}. Themes are not mutually exclusive, so shares sum "
         rf"to more than 100.}}"
         r"\label{tab:theme_summary}",
         r"\begingroup\small",
         r"\begin{tabularx}{\textwidth}{X r r}", r"\toprule",
         r"\textbf{Theme} & \textbf{Publications} & \textbf{\%} \\", r"\midrule"]
    for key, label, _ in ordered:
        c = counts.get(key, 0)
        L.append(rf"{tex_escape(label)} & {c} & {100 * c / n:.0f} \\")
    L += [r"\bottomrule", r"\end{tabularx}", r"\endgroup", r"\end{table}", ""]
    return "\n".join(L)


def build_codebook() -> str:
    # longtable, not tabularx: the term lists run past a single page. The second
    # column is sized by hand because longtable has no X column.
    header = [r"\toprule", r"\textbf{Theme} & \textbf{Terms} \\", r"\midrule"]
    L = ["% Auto-generated by scripts/lit_theme_synthesis.py -- do not edit by hand.",
         r"\begingroup\footnotesize",
         r"\begin{longtable}{@{}>{\raggedright\arraybackslash}p{3.4cm} "
         r">{\raggedright\arraybackslash}p{\dimexpr\textwidth-3.4cm-2\tabcolsep\relax}@{}}",
         r"\caption{\textbf{Codebook for thematic coverage.} A publication counts as addressing a "
         r"theme where its extracted challenge and recommendation text matches at least one "
         r"term listed for that theme. Terms match case-insensitively and on word stems, so "
         r"\texttt{data shar} covers sharing and shared. An ellipsis marks a gap of up to a "
         r"few words within the same sentence, and a slash separates alternatives. The exact "
         r"expressions are in the deposited analysis script.}"
         r"\label{tab:theme_codebook}\\"]
    L += header + [r"\endfirsthead",
                   r"\caption[]{\emph{(continued)}}\\"] + header + [r"\endhead",
                   r"\midrule \multicolumn{2}{r}{\emph{continued on next page}}\\",
                   r"\endfoot", r"\bottomrule", r"\endlastfoot"]
    for i, (_key, label, groups) in enumerate(THEMES):
        if i:
            L.append(r"\addlinespace")
        first = True
        for component, terms in groups:
            joined = ", ".join(r"\texttt{" + tex_escape(readable_term(t)) + "}"
                               for t in terms)
            head = tex_escape(label) if first else ""
            L.append(rf"{head} & \textit{{{tex_escape(component)}}}: {joined} \\")
            first = False
    L += [r"\end{longtable}", r"\endgroup", ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--audit", action="store_true", help="per-publication assignments and terms")
    ap.add_argument("--sample-for-labelling", type=int, metavar="N",
                    help="write N randomly chosen publications for hand-labelling")
    ap.add_argument("--seed", type=int, default=20260728)
    ap.add_argument("--labels-out", type=Path, default=Path("theme_labels_blank.csv"))
    ap.add_argument("--exclude", type=Path, action="append", metavar="LABELS",
                    help="earlier sample to exclude, so a holdout stays held out (repeatable)")
    ap.add_argument("--validate", type=Path, metavar="LABELS",
                    help="score the codebook against a hand-labelled file")
    ap.add_argument("--out-dir", type=Path, action="append")
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()

    recs = load(args.run)
    n = len(recs)
    if not n:
        raise SystemExit("error: no included publications")
    print(f"  {args.run.name}: {n} included publications, threshold {MIN_HITS} term\n")

    if args.sample_for_labelling:
        sample_for_labelling(recs, args.sample_for_labelling, args.seed, args.labels_out, args.exclude)
        return 0

    if args.validate:
        validate(recs, args.validate)
        return 0

    counts = collections.Counter()
    uncovered = []
    for r in recs:
        a = assign(r)
        if not a:
            uncovered.append(r.get(COL_TITLE, "")[:62])
        for k in a:
            counts[k] += 1

    for key, label, _g in sorted(THEMES, key=lambda t: -counts.get(t[0], 0)):
        c = counts.get(key, 0)
        print(f"    {c:4d}  {100 * c / n:5.0f}%  {label}")
    print(f"\n    addressing no theme: {len(uncovered)}")
    for t in uncovered[:8]:
        print(f"      {t!r}")

    if args.audit:
        # A component sitting at zero means that half of the theme's label is
        # unserved by the codebook, which a flat term list hides.
        print("\n  coverage by label component:")
        for _key, label, groups in THEMES:
            print(f"    {label}")
            for component, terms in groups:
                c = sum(1 for r in recs
                        if any(re.search(t, text_of(r), re.I) for t in terms))
                dead = sum(1 for t in terms
                           if not any(re.search(t, text_of(r), re.I) for r in recs))
                note = f"   ({dead}/{len(terms)} terms never match)" if dead else ""
                print(f"      {c:4d}  {component}{note}")

        print("\n  per-publication assignments:")
        for r in recs:
            a = assign(r)
            print(f"    {(r.get(COL_TITLE) or '')[:52]:54} "
                  f"{', '.join(sorted(a)) or '(none)'}")
            for k, terms in sorted(a.items()):
                print(f"        {k:18} <- {', '.join(terms)}")

    if args.check_only:
        print("\n  --check-only: no files written")
        return 0

    for name, text in [("theme_summary.tex", build_table(counts, n)),
                       ("theme_codebook.tex", build_codebook())]:
        for d in (args.out_dir or OUT_DIRS):
            d = Path(d)
            d.mkdir(parents=True, exist_ok=True)
            p = d / name
            p.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
            try:
                print(f"  wrote {p.relative_to(PROJECT_ROOT)}")
            except ValueError:
                print(f"  wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

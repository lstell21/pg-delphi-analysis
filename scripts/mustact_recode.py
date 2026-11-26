#!/usr/bin/env python3
"""
Blind recoding of who must act on each consensus statement.

Table 1 labels each statement with the parties that must act on it: M modelling
groups, A public health agencies, P policy advisors. That labelling was a team
judgement made without a second, independent coder. This script supports a
blind recode by however many co-authors return a complete sheet, identified
only as C1 to Ck.

  The coders' workbooks came from an export mode that copies the coding rule
  from the Methods. It is not part of this release, which reads the sheets
  in the CSV form the data deposit carries.

  score   reads the k returned sheets, by default every .csv in
          data/delphi/mustact/, and names their coders C1 to Ck in
          alphabetical order of file name. A CSV sheet, the form the data
          deposit carries, has the columns Statement, M, A, P and Recalled
          (and Comment, if deposited with it), 1 for marked and empty
          otherwise. The mapping from file to ID goes to
          coder_ids.csv next to agreement.json and nowhere else, so every
          committed output carries the IDs only. A sheet must give each of the
          39 recommendations at least one party; an incomplete sheet stops the
          run with its name and statements, never dropped silently.

          A08, the consensus principle, carries no label (Leonard, 5 November
          2026). It enters no statistic, no count and not the majority rule;
          everything below covers the 39 recommendations. The listing still
          shows each coder's A08 coding, with "--" for the study team.

          It reports Krippendorff's alpha (nominal) for the label sets across
          all k coders, and for each pair of coders the per-party percent
          agreement and Cohen's kappa, with exact agreement and alpha on the
          label sets. The same again without recalled codings: in the
          all-coder alpha a recalled coding counts as missing, and in each pair
          the statements either coder recalled are dropped. And each coder's
          agreement with the published codes, which only this mode reads.

          The final labels follow one rule: a published label changes only
          where more than half of the k coders disagree with it, so a tie keeps
          it, and with one coder nothing changes. With two coders this is the
          majority of the three codings. It lists every label the rule changes
          and recounts the must-act split under the final labels. Writes
          agreement.json and tables/mustact_recoding.tex. The study team's
          labels are main_text_tables.STUDY_TEAM_AUDIENCE, which never
          changes; the final labels are applied there by hand, as
          RECODING_CHANGES, and this mode reports whether they still match.

Every co-author has seen Table 1 in earlier drafts, so a coder may remember a
published code. The Recalled column records that, statement by statement, and
the recall-free agreement shows how much it matters.

Usage:
    python scripts/mustact_recode.py score [--sheets FILE ...]
                                           [--out-dir DIR] [--tables-dir DIR]
    python scripts/mustact_recode.py placeholder [--tables-dir DIR]
        writes the table with empty agreement cells until the sheets return
"""
import argparse
import csv
import itertools
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from r4_statements import R4_STATEMENTS, ordered_ids  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data" / "generated" / "mustact"
RETURNED_DIR = PROJECT_ROOT / "data" / "delphi" / "mustact"
CODERS = ("C1", "C2")   # the sheets export writes
PARTIES = ("M", "A", "P")
SEED = 20261103

# Party definitions, verbatim from the Table 1 caption.
PARTY_TEXT = {
    "M": "modelling groups",
    "A": "public health agencies, including funders and providers of national "
         "data infrastructure",
    "P": "policy advisors",
}

# The rule is read from the Methods at export time, so the sheet carries the
# wording the paper reports. It starts at this sentence and runs two sentences.
RULE_START = "We applied one rule:"
RULE_SENTENCES = 2

COLUMNS = ["Order", "Statement ID", "Statement (Round 4 wording)", "M", "A", "P",
           "Recalled", "Comment"]
FIRST_ROW = 2   # row 1 is the header
MARKED = {"1", "x", "yes", "y"}   # a cell counts as marked if it holds one of these
# A sheet in the deposit's CSV form; "Comment" may follow.
CSV_COLUMNS = ["Statement", "M", "A", "P", "Recalled"]
SHEET_GLOBS = ("*.csv",)


def csv_rows(path: Path) -> list:
    """(statement, M, A, P, Recalled, Comment) per row of a sheet in CSV form."""
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader, [])
        if header[:len(CSV_COLUMNS)] != CSV_COLUMNS:
            raise SystemExit(f"error: {path.name}: unexpected header {header}")
        comment = header.index("Comment") if "Comment" in header else None
        rows = [r + [""] * (len(header) - len(r)) for r in reader if r and r[0]]
        return [(r[0], *r[1:5], r[comment] if comment is not None else None) for r in rows]


def sheet_rows(path: Path) -> list:
    return csv_rows(path)


def marked(value, path, sid, column) -> bool:
    text = "" if value is None else str(value).strip().lower()
    if text and text not in MARKED:
        raise SystemExit(f"error: {path.name}: {sid} {column} holds {value!r}; "
                         "use 1 or leave it empty")
    return bool(text)


def order_sheets(paths) -> list:
    """Sheets in coder-ID order: alphabetical by file name, so the first is C1."""
    return sorted(paths, key=lambda p: (p.name.lower(), p.name))


def returned_sheets(directory: Path = None) -> list:
    """The returned sheets in coder-ID order. Excel's "~$" lock files, left
    beside a sheet that is open, are not sheets."""
    directory = directory or RETURNED_DIR
    return order_sheets(p for g in SHEET_GLOBS for p in directory.glob(g)
                        if not p.name.startswith("~$"))


def read_sheet(path: Path) -> tuple:
    """({statement id: frozenset of parties}, {ids marked as recalled}) from a
    filled-in coder sheet, .xlsx or CSV."""
    codes, recalled = {}, set()
    for sid, m, a, p, rec, _comment in sheet_rows(path):
        codes[sid] = frozenset(party for party, v in zip(PARTIES, (m, a, p))
                               if marked(v, path, sid, party))
        if marked(rec, path, sid, "Recalled"):
            recalled.add(sid)
    if set(codes) != set(R4_STATEMENTS):
        missing = sorted(set(R4_STATEMENTS) - set(codes))
        extra = sorted(set(codes) - set(R4_STATEMENTS))
        raise SystemExit(f"error: {path.name}: missing {missing}, unexpected {extra}")
    return codes, recalled


def published_codes() -> dict:
    """Table 1's labels, for the 39 recommendations: A08 carries none. Only
    score reads them; export never does."""
    from main_text_tables import STUDY_TEAM_AUDIENCE
    return {s: frozenset(STUDY_TEAM_AUDIENCE[s].split(", ")) for s in STUDY_TEAM_AUDIENCE}


def published_text(published: dict, s: str) -> str:
    """The study team's label for the listing, "--" for A08."""
    return label_text(published[s]) if s in published else "--"


def recommendations() -> list:
    """The 39 statements typed as recommendations, A08 being the principle."""
    from main_text_tables import TYPE, PRINCIPLE
    return [s for s in ordered_ids() if TYPE[s] != PRINCIPLE]


def incomplete(codes: dict) -> list:
    """Recommendations a sheet leaves without any party. A08 enters no
    statistic, so a sheet that leaves it empty is still complete."""
    return [s for s in recommendations() if not codes[s]]


def final(published: dict, codings: list) -> dict:
    """Per statement, the published labels, each reversed where more than half
    of the k coders disagree with it. A tie keeps the published label, and with
    one coder nothing changes. With two coders this is the majority of the
    three codings (published, C1, C2)."""
    k = len(codings)
    out = {}
    for s, labels in published.items():
        against = {p for p in PARTIES if 2 * sum((p in c[s]) != (p in labels) for c in codings) > k}
        out[s] = frozenset(labels ^ against) if k >= 2 else labels
    return out


def must_act_counts(codes: dict, ids: list) -> dict:
    return {"modelling_group_only": sum(1 for s in ids if codes[s] == frozenset({"M"})),
            "involving_agencies": sum(1 for s in ids if "A" in codes[s])}


def label_text(codes) -> str:
    return ", ".join(sorted(codes, key=PARTIES.index))


def final_report(published: dict, codings: dict, recs: list) -> dict:
    """Labels the rule changes and the must-act counts, over the recommendations,
    and every coding per statement, A08 included, for the listing."""
    finals = final(published, list(codings.values()))
    changes = [{"statement": s, "party": p, "change": "added" if p in finals[s] else "removed"}
               for s in recs for p in PARTIES if (p in finals[s]) != (p in published[s])]
    return {
        "rule": "a published label changes only where more than half of the k coders "
                "disagree with it; a tie keeps it, and with one coder nothing changes",
        "k": len(codings),
        "changes": changes,
        "labels": {s: label_text(finals[s]) for s in recs},
        "codings": {s: {"published": published_text(published, s),
                        **{cid: label_text(c[s]) for cid, c in codings.items()}}
                    for s in ordered_ids()},
        "counts": {name: must_act_counts(codes, recs)
                   for name, codes in (("published", published), ("final", finals))},
    }


def cohen_kappa(a: list, b: list):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in set(a) | set(b))
    return None if pe == 1 else (po - pe) / (1 - pe)


def krippendorff_alpha_nominal(units: list):
    """Alpha for nominal data from a list of per-unit value lists (no missing values)."""
    coincidence = Counter()
    for values in units:
        m = len(values)
        if m < 2:
            continue
        for i, x in enumerate(values):
            for j, y in enumerate(values):
                if i != j:
                    coincidence[(x, y)] += 1 / (m - 1)
    n_c = Counter()
    for (x, _), w in coincidence.items():
        n_c[x] += w
    n = sum(n_c.values())
    d_o = sum(w for (x, y), w in coincidence.items() if x != y)
    d_e = sum(n_c[x] * n_c[y] for x in n_c for y in n_c if x != y) / (n - 1)
    return None if d_e == 0 else 1 - d_o / d_e


def compare(a: dict, b: dict, ids: list, alpha: bool = False) -> dict:
    """Agreement of two codings over the given statements."""
    out = {"n_statements": len(ids), "parties": {}, "label_sets": {}}
    if not ids:
        return out
    for party in PARTIES:
        x = [party in a[s] for s in ids]
        y = [party in b[s] for s in ids]
        out["parties"][party] = {
            "labelled": [sum(x), sum(y)],
            "agreement_pct": 100 * sum(p == q for p, q in zip(x, y)) / len(ids),
            "cohen_kappa": cohen_kappa(x, y),
        }
    sets_a = [",".join(sorted(a[s])) or "none" for s in ids]
    sets_b = [",".join(sorted(b[s])) or "none" for s in ids]
    out["label_sets"] = {
        "exact_agreement_pct": 100 * sum(x == y for x, y in zip(sets_a, sets_b)) / len(ids),
        "disagreements": [s for s, x, y in zip(ids, sets_a, sets_b) if x != y],
    }
    if alpha:
        out["label_sets"]["krippendorff_alpha_nominal"] = krippendorff_alpha_nominal(
            [[x, y] for x, y in zip(sets_a, sets_b)])
    return out


def compare_all(codings: dict, ids: list, recalled: dict = None) -> dict:
    """Agreement across all coders. With recalled given, a recalled coding counts
    as missing, and a statement left with fewer than two codings drops out."""
    present = {s: [c for c in codings if not (recalled and s in recalled[c])] for s in ids}
    kept = [s for s in ids if len(present[s]) >= 2]
    out = {"n_statements": len(kept), "parties": {}, "label_sets": {}}
    if recalled is not None:
        out["recalled_codings_removed"] = sum(len(codings) - len(present[s]) for s in ids)
    if not kept:
        return out
    for party in PARTIES:
        same = sum(len({party in codings[c][s] for c in present[s]}) == 1 for s in kept)
        out["parties"][party] = {"agreement_pct": 100 * same / len(kept)}
    sets = {s: [",".join(sorted(codings[c][s])) or "none" for c in present[s]] for s in kept}
    out["label_sets"] = {
        "exact_agreement_pct": 100 * sum(len(set(v)) == 1 for v in sets.values()) / len(kept),
        "disagreements": [s for s in kept if len(set(sets[s])) > 1],
        "krippendorff_alpha_nominal": krippendorff_alpha_nominal(list(sets.values())),
    }
    return out


def score(codings: dict, recalled: dict = None, published: dict = None, recs: list = None) -> dict:
    """codings and recalled are keyed by coder ID, C1 to Ck. Every statistic
    covers the recommendations only; A08 carries no label."""
    ids = recs if recs is not None else recommendations()
    recalled = recalled or {c: set() for c in codings}
    published = published or published_codes()
    result = {"k": len(codings), "recalled": {c: sorted(recalled[c]) for c in codings}, "pairs": {}}
    for a, b in itertools.combinations(codings, 2):
        pair = compare(codings[a], codings[b], ids, alpha=True)
        kept = [s for s in ids if s not in recalled[a] and s not in recalled[b]]
        pair["without_recalled"] = {"removed": len(ids) - len(kept),
                                    **compare(codings[a], codings[b], kept, alpha=True)}
        result["pairs"][f"{a} vs {b}"] = pair
    if len(codings) >= 2:
        result["all_coders"] = compare_all(codings, ids)
        result["all_coders"]["without_recalled"] = compare_all(codings, ids, recalled)
    result["against_published"] = {c: compare(codings[c], published, ids) for c in codings}
    result["final_labels"] = final_report(published, codings, ids)
    result["robustness"] = robustness(codings, published, ids)
    return result


def robustness(codings: dict, published: dict, ids: list) -> dict:
    """How far the coders' label sets support the text's statements about who
    must act, over the recommendations. "Beyond the modelling group" means the
    set holds A or P."""
    def beyond(codes):
        return sum(1 for s in ids if codes[s] & {"A", "P"})

    def policy(codes):
        return sum(1 for s in ids if "P" in codes[s])

    finals = final(published, list(codings.values()))

    def spread(count, test):
        per_coder = {c: count(codes) for c, codes in codings.items()}
        return {"per_coder": per_coder, "min": min(per_coder.values()), "max": max(per_coder.values()),
                "study_team": {name: {"count": count(codes), "statements": [s for s in ids if test(codes[s])]}
                               for name, codes in (("original", published), ("final", finals))}}

    unanimous = [{"statement": s, "label_set": label_text(next(iter(codings.values()))[s])}
                 for s in ids if len({codings[c][s] for c in codings}) == 1]
    by_parties = {}
    for name, test in (("several_parties", lambda f: len(f) > 1), ("one_party", lambda f: len(f) == 1)):
        group = [s for s in ids if test(finals[s])]
        distinct = [len({codings[c][s] for c in codings}) for s in group]
        by_parties[name] = {"n": len(group), "statements": group,
                            "mean_distinct_sets": sum(distinct) / len(group) if group else None}
    return {
        "n_recommendations": len(ids),
        "beyond_modelling_group": spread(beyond, lambda labels: bool(labels & {"A", "P"})),
        "policy_advisor": spread(policy, lambda labels: "P" in labels),
        "unanimous": unanimous,
        "distinct_sets_by_parties": {
            "split": "by the number of parties in the final label", **by_parties},
    }


def rounded(obj, places=3):
    """Copy of a result with every float rounded, for the JSON and the console.
    The LaTeX table formats the unrounded values, so it never rounds twice."""
    if isinstance(obj, float):
        return round(obj, places)
    if isinstance(obj, dict):
        return {k: rounded(v, places) for k, v in obj.items()}
    if isinstance(obj, list):
        return [rounded(v, places) for v in obj]
    return obj


def fmt(x, pct=False) -> str:
    if x is None:
        return "--"
    return f"{x:.1f}" if pct else f"{x:.2f}"


def table_row(name: str, c: dict) -> str:
    cells = [name, str(c["n_statements"])]
    for party in PARTIES:
        p = c["parties"].get(party)
        cells += [fmt(p["agreement_pct"], True), fmt(p.get("cohen_kappa"))] if p else ["--", "--"]
    ls = c["label_sets"]
    cells += [fmt(ls.get("exact_agreement_pct"), True), fmt(ls.get("krippendorff_alpha_nominal"))]
    return " & ".join(cells) + " \\\\"


def agreement_rows(result: dict) -> list:
    """One row per coder pair and one for all coders, then each coder against the
    published labels. If any coding was marked as recalled, each pair and the
    all-coders row is followed by the same without the recalled codings, indented
    beneath its comparison, which keeps the first column narrow. With none marked,
    those rows would repeat their comparisons, so the caption says so instead."""
    recalled = any(result.get("recalled", {}).values())
    rows = []
    for name, pair in result["pairs"].items():
        rows.append(table_row(name, pair))
        if recalled:
            rows.append(table_row("\\quad recalled removed", pair["without_recalled"]))
    if "all_coders" in result:
        every = result["all_coders"]
        rows.append(table_row("All coders", every))
        if recalled:
            rows.append(table_row("\\quad recalled removed", every["without_recalled"]))
    rows += [table_row(f"{c} vs study team", r) for c, r in result["against_published"].items()]
    return rows


NUMBER_WORDS = "zero one two three four five six seven eight nine ten eleven twelve".split()


def caption(result: dict) -> str:
    """The caption: the number of coders and recommendations from the data, and
    whether any coding was marked as recalled. Before any sheet is scored, the
    placeholder caption."""
    k = result["k"]
    if not isinstance(k, int):
        return (f"TODO(Part B): blind recoding of who must act, {k} coders, "
                f"{len(R4_STATEMENTS)} statements.")
    coders = NUMBER_WORDS[k].capitalize() if k < len(NUMBER_WORDS) else str(k)
    recalled = sum(len(v) for v in result.get("recalled", {}).values())
    # With no coding marked as recalled, the table has no recall-free rows, and the
    # caption says why.
    recall = (" No coder marked a statement whose study-team label they recalled "
              "(Methods), so every coding enters the statistics." if not recalled else
              f" \\pending{{CHECK: {recalled} codings were marked as recalled}}")
    # A08 is the consensus principle: the coders labelled it, but it has no final label.
    a08 = {c: v for c, v in result["final_labels"]["codings"].get("A08", {}).items()
           if c != "published"}
    given = set(a08.values())
    if len(given) == 1 and "" not in given:
        a08_text = (f"All {NUMBER_WORDS[k] if k < len(NUMBER_WORDS) else k} coders labelled "
                    f"A08 {given.pop().replace(', ', '')}, but as the consensus principle it "
                    "places no duty on anyone (Methods), so it has no final label and enters "
                    "no statistic.")
    elif any(a08.values()):
        a08_text = ("The coders also labelled A08, but as the consensus principle it places "
                    "no duty on anyone (Methods), so it has no final label and enters no "
                    "statistic.")
    else:
        a08_text = "A08 carries no label and enters no statistic."
    return ("\\textbf{Independent recoding of who must act.} "
            f"{coders} co-authors who had not taken part in the original coding (C1 to C{k}) "
            "each labelled the statements from the coding rule alone. The upper part gives "
            f"agreement over the {len(recommendations())} recommendations: per party, as "
            "percentage agreement and Cohen's $\\kappa$, and for the whole label set, as exact "
            "agreement and Krippendorff's $\\alpha$. It compares each pair of coders, all coders "
            f"together, and each coder with the study team.{recall} The lower part lists every "
            "coding per statement, with the study team's label and the final label after the "
            f"majority rule. {a08_text}")


def build_table(result: dict) -> str:
    """One longtable in three parts: agreement, the must-act counts, and every
    coding per statement. The listing runs to 40 rows, so with k coders the
    whole no longer fits a float; a longtable breaks across pages and keeps one
    caption, label and number."""
    k = result["k"]
    fin = result["final_labels"]
    return (
        "% Auto-generated by scripts/mustact_recode.py -- do not edit by hand.\n"
        + ("% TODO(Part B): replace the placeholder caption with final wording.\n"
           if not isinstance(k, int) else "") +
        "\\begingroup\\footnotesize\\setlength{\\tabcolsep}{3.25pt}\n"
        "\\begin{longtable}{@{}l r r r r r r r r r@{}}\n"
        f"\\caption{{{caption(result)}}}\n"
        "\\label{tab:mustact_recoding}\\\\\n\\toprule\n\\endfirsthead\n"
        "\\caption[]{\\emph{(continued)}}\\\\\n\\toprule\n\\endhead\n"
        "\\midrule \\multicolumn{10}{r}{\\emph{continued on next page}}\\\\\n\\endfoot\n"
        "\\bottomrule\n\\endlastfoot\n"
        " & & \\multicolumn{2}{c}{M} & \\multicolumn{2}{c}{A} & \\multicolumn{2}{c}{P}"
        " & \\multicolumn{2}{c}{Label set} \\\\\n"
        "\\cmidrule(lr){3-4}\\cmidrule(lr){5-6}\\cmidrule(lr){7-8}\\cmidrule(l){9-10}\n"
        "Comparison & $n$ & \\% & $\\kappa$ & \\% & $\\kappa$ & \\% & $\\kappa$"
        " & \\% & $\\alpha$ \\\\\n\\midrule\n"
        + "\n".join(agreement_rows(result)) +
        "\n\\midrule\n"
        + counts_rows(fin) +
        "\\midrule\n"
        + listing_rows(fin) +
        "\\end{longtable}\n\\endgroup\n"
    )


def counts_rows(fin: dict) -> str:
    """Must-act counts over the recommendations under the published and the
    final labels, and the labels the rule changes."""
    c = fin["counts"]
    final_counts = c["final"] or {}
    rows = [f"{name} & {c['published'][key]} & {final_counts.get(key, '--')} \\\\"
            for name, key in (("Modelling group only", "modelling_group_only"),
                              ("Involving an agency", "involving_agencies"))]
    if fin["changes"] is None:
        changes = "\\pending{PENDING: awaiting the coders' sheets}"
    else:
        changes = "; ".join(f"{ch['statement']} {ch['party']} {ch['change']}" for ch in fin["changes"])
    return (
        "% Final labels: a study-team label changes where more than half of the coders disagree."
        " TODO(Part B): note wording.\n"
        # The label wraps onto two lines, so the first column is no wider than its
        # other labels and the table fits the text width (CH-67).
        f"\\multicolumn{{1}}{{@{{}}p{{8.5em}}}}{{\\raggedright Must act, {len(recommendations())} "
        "recommendations} & Study team & Final \\\\\n\\midrule\n"
        + "\n".join(rows) +
        f"\n\\multicolumn{{10}}{{@{{}}p{{0.9\\linewidth}}@{{}}}}{{Labels the rule changes: "
        f"{changes or 'none'}.}} \\\\\n"
    )


def listing_rows(fin: dict) -> str:
    """Every coding per statement, one column per coder. A final label set that
    differs from the published one is set in bold. A08 has no final label."""
    ids = list(ordered_ids())
    codings = fin["codings"]
    coders = [c for c in codings[ids[0]] if c != "published"]
    short = lambda text: text.replace(", ", "") or "none"
    if not coders:                          # the placeholder: published labels only
        head = ["Statement", "Study team", "C1--C$k$", "Final"]
        rows = [[s, short(codings[s]["published"]), "--", "--"] for s in ids]
    else:
        head = ["Statement", "Study team", *coders, "Final"]
        rows = []
        for s in ids:
            mark = short(fin["labels"].get(s, "--"))
            if s in fin["labels"] and fin["labels"][s] != codings[s]["published"]:
                mark = f"\\textbf{{{mark}}}"
            rows.append([s, short(codings[s]["published"]), *[short(codings[s][c]) for c in coders], mark])
    return (" & ".join(head) + " \\\\\n\\midrule\n"
            + "\n".join(" & ".join(r) + " \\\\" for r in rows) + "\n")


def placeholder_result() -> dict:
    """The table's layout before the coders' sheets come back: every agreement
    cell empty, the published must-act counts and labels filled in, the final
    labels pending."""
    ids = list(ordered_ids())
    published = published_codes()
    empty = {"n_statements": "--", "parties": {}, "label_sets": {}}
    counts = must_act_counts(published, recommendations())
    return {"k": "$k$",
            "pairs": {"C$i$ vs C$j$": {**empty, "without_recalled": empty}},
            "all_coders": {**empty, "without_recalled": empty},
            "against_published": {"C$i$": empty},
            "final_labels": {"changes": None,
                             "codings": {s: {"published": published_text(published, s)} for s in ids},
                             "counts": {"published": counts, "final": None}}}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    ph = sub.add_parser("placeholder", help="write the table with empty cells until the sheets return")
    ph.add_argument("--tables-dir", type=Path, default=PROJECT_ROOT / "tables")
    sc = sub.add_parser("score")
    sc.add_argument("--sheets", type=Path, nargs="+", default=None,
                    help=f"the returned sheets (default: every {' or '.join(SHEET_GLOBS)} "
                         f"in {RETURNED_DIR})")
    sc.add_argument("--out-dir", type=Path, default=OUT_DIR)
    sc.add_argument("--tables-dir", type=Path, default=PROJECT_ROOT / "tables")
    args = ap.parse_args()

    if args.mode == "placeholder":
        args.tables_dir.mkdir(parents=True, exist_ok=True)
        tex_path = args.tables_dir / "mustact_recoding.tex"
        tex_path.write_text(build_table(placeholder_result()), encoding="utf-8")
        print(f"wrote {tex_path} (placeholder: no coder sheets scored yet)")
        return

    # Coder IDs follow the alphabetical order of the file names.
    sheets = order_sheets(args.sheets) if args.sheets else returned_sheets()
    if not sheets:
        raise SystemExit(f"error: no returned sheets to score in {RETURNED_DIR}")
    files = {f"C{n}": path for n, path in enumerate(sheets, start=1)}
    read = {c: read_sheet(path) for c, path in files.items()}
    gaps = {c: incomplete(codes) for c, (codes, _) in read.items()}
    if any(gaps.values()):
        raise SystemExit("error: incomplete sheets, nothing scored:\n" + "\n".join(
            f"  {files[c].name}: no party for {', '.join(g)}" for c, g in gaps.items() if g))
    result = score({c: codes for c, (codes, _) in read.items()},
                   {c: recalled for c, (_, recalled) in read.items()})

    args.out_dir.mkdir(parents=True, exist_ok=True)
    # The only place that ties a coder ID to a file, and so to a person.
    id_path = args.out_dir / "coder_ids.csv"
    with open(id_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["coder", "file"])
        writer.writerows((c, path.name) for c, path in files.items())
    json_path = args.out_dir / "agreement.json"
    json_path.write_text(json.dumps(rounded(result), indent=2), encoding="utf-8")
    args.tables_dir.mkdir(parents=True, exist_ok=True)
    tex_path = args.tables_dir / "mustact_recoding.tex"
    tex_path.write_text(build_table(result), encoding="utf-8")

    shown = rounded(result)
    print(f"  k = {shown['k']} coders")
    rows = []
    for name, pair in shown["pairs"].items():
        rows += [(name, pair), (f"{name}, recalled removed ({pair['without_recalled']['removed']} "
                                f"statements)", pair["without_recalled"])]
    if "all_coders" in shown:
        every = shown["all_coders"]
        rows += [("All coders", every),
                 (f"All coders, recalled removed ({every['without_recalled']['recalled_codings_removed']} "
                  "codings)", every["without_recalled"])]
    rows += [(f"{c} vs study team", r) for c, r in shown["against_published"].items()]
    for name, c in rows:
        parts = ", ".join(f"{p} {v['agreement_pct']}%"
                          + (f" (kappa {v['cohen_kappa']})" if "cohen_kappa" in v else "")
                          for p, v in c["parties"].items())
        ls = c["label_sets"]
        alpha = f", alpha {ls['krippendorff_alpha_nominal']}" if "krippendorff_alpha_nominal" in ls else ""
        print(f"  {name} (n = {c['n_statements']}): {parts}; "
              f"exact {ls.get('exact_agreement_pct')}%{alpha}")
    fin = shown["final_labels"]
    changed = ["%s %s %s" % (c["statement"], c["party"], c["change"]) for c in fin["changes"]]
    print(f"  final labels change: {'; '.join(changed) or 'none'}")
    for name in ("published", "final"):
        print(f"  {name}, {len(recommendations())} recommendations: {fin['counts'][name]}")
    rob = shown["robustness"]
    for name in ("beyond_modelling_group", "policy_advisor"):
        r = rob[name]
        team = r["study_team"]
        print(f"  {name}: {r['per_coder']}; min {r['min']}, max {r['max']}; study team "
              f"{team['original']['count']} with its original labels, {team['final']['count']} with the final")
    print("  unanimous: " + (", ".join(f"{u['statement']} {{{u['label_set']}}}" for u in rob["unanimous"])
                             or "none"))
    print("  distinct label sets per statement: " + "; ".join(
        f"{name.replace('_', ' ')} n = {g['n']}, mean {g['mean_distinct_sets']}"
        for name, g in rob["distinct_sets_by_parties"].items() if name != "split"))
    from main_text_tables import AUDIENCE
    stale = sorted(s for s, labels in fin["labels"].items() if AUDIENCE.get(s) != labels)
    print("  main_text_tables.AUDIENCE " + (f"differs from the final labels for {', '.join(stale)}; "
                                            "update RECODING_CHANGES" if stale else
                                            "holds these final labels"))
    print(f"wrote {id_path}\nwrote {json_path}\nwrote {tex_path}")


if __name__ == "__main__":
    main()

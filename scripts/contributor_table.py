#!/usr/bin/env python3
"""
Disciplinary composition of the Delphi panel.

data/delphi/contributors/disciplines.csv holds one row per panellist: name, category
(the discipline we assign) and basis (what the assignment rests on, such as
affiliation or publication record). Categories are filled in by hand. This script
counts panellists per category, writes the counts to discipline_counts.csv next
to it (category, n), and writes tables/contributor_disciplines.tex.

The per-name file stays local and is never deposited. The data deposit carries
the counts file only, and --from-counts builds the same table from it alone.

--from-replies writes the counts from the replies instead: replies.txt holds one
reported discipline per line as written (lines starting with # are ignored),
grouped case-insensitively by REPLY_GROUPS, and assigned.csv (category, n,
basis) holds disciplines assigned without a reply. "Not yet reported" fills up
to the contributors of the byline note. Both files stay local; the counts file
records how many of each category were assigned.

The panel is read from the byline note of 00_main.tex: the authors listed
alphabetically from the first to the last name it gives, the infoXpand
consortium panellists it names, and the one panellist it names who is not an
author. Every run on the per-name file checks it against that list, so the two
cannot drift.

Usage:
    python scripts/contributor_table.py --init         write the CSV with names only (never overwrites)
    python scripts/contributor_table.py                check the CSV, write the counts and the table
    python scripts/contributor_table.py --from-counts  write the table from the counts alone
    python scripts/contributor_table.py --from-replies write the counts and the table from the replies
"""
import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "delphi" / "contributors" / "disciplines.csv"
COUNTS_PATH = PROJECT_ROOT / "data" / "delphi" / "contributors" / "discipline_counts.csv"
REPLIES_PATH = PROJECT_ROOT / "data" / "delphi" / "contributors" / "replies.txt"
ASSIGNED_PATH = PROJECT_ROOT / "data" / "delphi" / "contributors" / "assigned.csv"
TABLE_OUT = PROJECT_ROOT / "tables" / "contributor_disciplines.tex"
FIELDS = ["name", "category", "basis"]
UNASSIGNED = "Not yet assigned"

ACCENTS = {'"': "\u0308", "'": "\u0301", "`": "\u0300", "v": "\u030c", "^": "\u0302"}


def untex(s: str) -> str:
    """M\\"as -> Mäs, and the few other accent macros a name can carry."""
    import unicodedata
    s = re.sub(r'\\([\"\'`^v])\{?([A-Za-z])\}?', lambda m: m.group(2) + ACCENTS[m.group(1)], s)
    return unicodedata.normalize("NFC", s)


def authors(src: str) -> list:
    """Author names in byline order, from the centred title block."""
    block = re.search(r"\{\\large\s*(.+?)\\par\}", src, re.S).group(1)
    names = []
    for line in block.splitlines():
        line = re.sub(r"\\alc?\{[^}]*\}|\$\^\{[^}]*\}\$", "", line).strip().rstrip(",").strip()
        if line:
            names.append(untex(line))
    return names


def panel(src: str) -> tuple:
    """(panel names, author names) from the byline note and the author block."""
    # The note names the study team's Round 1 member (A. Calero Valdez) only after
    # "acknowledged below.", so the panel read here leaves the study team out. Its
    # first sentence was split in two (CH-61); both wordings are read.
    found = re.search(r"The contributors(?:,| are) everyone outside the study team who took part "
                      r"in at\s+least one Delphi round(?:,|\.\s+They) include all authors"
                      r".+?acknowledged below\.", src, re.S)
    if found is None:
        raise SystemExit("error: the byline note no longer starts 'The contributors are everyone "
                         "outside the study team who took part in at least one Delphi round. They "
                         "include all authors'; update panel()")
    note = found.group(0)
    note = " ".join(note.split())
    first, last = re.search(r"alphabetically from (.+?) to (.+?), together with", note).groups()
    consortium = re.search(r"together with (.+?) of the infoXpand consortium", note).group(1)
    extra = re.search(r"consortium, and (.+?), who is acknowledged below", note).group(1)
    names = authors(src)
    first, last = untex(first), untex(last)
    block = names[names.index(first):names.index(last) + 1]
    cons = [untex(n.strip()) for n in re.split(r",\s*(?:and\s+)?|\s+and\s+", consortium) if n.strip()]
    missing = [n for n in cons if n not in names]
    if missing:
        raise SystemExit(f"error: consortium panellists not among the authors: {missing}")
    return block + cons + [untex(extra)], names


def read_csv() -> list:
    with CSV_PATH.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def count_categories(rows: list) -> list:
    """(category, n) per category, largest first; an empty category counts as
    UNASSIGNED, the label the table prints."""
    counts = Counter((r["category"] or "").strip() or UNASSIGNED for r in rows)
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def write_counts(counts: list) -> None:
    """counts as (category, n) or (category, n, assigned); the file always
    carries the assigned column."""
    COUNTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with COUNTS_PATH.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["category", "n", "assigned"])
        w.writerows((*row[:2], row[2] if len(row) > 2 else 0) for row in counts)


def read_counts() -> list:
    """(category, n, assigned) per category, largest first. A counts file
    written before the assigned column existed reads as 0 assigned."""
    if not COUNTS_PATH.exists():
        raise SystemExit(f"error: {COUNTS_PATH} not found")
    with COUNTS_PATH.open(encoding="utf-8", newline="") as fh:
        rows = [(r["category"], int(r["n"]), int(r.get("assigned") or 0)) for r in csv.DictReader(fh)]
    return sorted(rows, key=lambda kv: (-kv[1], kv[0]))


# Reply text, lower-cased, to the category the table prints. A reply not
# listed here stops the script, so a new spelling is grouped by hand once.
REPLY_GROUPS = {
    "mathematical or computational modelling": "Mathematical or computational modelling",
    "mathematical modelling": "Mathematical or computational modelling",
    "epidemiology": "Epidemiology",
    "health economics": "Health economics",
    "clinical medicine": "Clinical medicine",
    "medicine": "Clinical medicine",
    "social sciences (including sociology, political science and science and technology studies)":
        "Social sciences",
    "public health or health policy": "Public health or health policy",
    "public health": "Public health or health policy",
    "health policy": "Public health or health policy",
    "biostatistics": "Biostatistics",
    "computer science": "Computer science",
}


def read_replies() -> list:
    """The category of each reply in replies.txt, in file order."""
    if not REPLIES_PATH.exists():
        raise SystemExit(f"error: {REPLIES_PATH} not found")
    lines = [line.strip() for line in REPLIES_PATH.read_text(encoding="utf-8").splitlines()]
    replies = [line for line in lines if line and not line.startswith("#")]
    unknown = sorted({r for r in replies if " ".join(r.split()).lower() not in REPLY_GROUPS})
    if unknown:
        raise SystemExit("error: replies not in REPLY_GROUPS, nothing written:\n"
                         + "\n".join(f"  {r!r}" for r in unknown))
    return [REPLY_GROUPS[" ".join(r.split()).lower()] for r in replies]


def read_assigned() -> list:
    """(category, n) rows of assigned.csv; an empty list if the file is absent."""
    if not ASSIGNED_PATH.exists():
        return []
    with ASSIGNED_PATH.open(encoding="utf-8", newline="") as fh:
        rows = [(r["category"].strip(), int(r["n"])) for r in csv.DictReader(fh)]
    unknown = sorted({c for c, _ in rows if c not in REPLY_GROUPS.values()})
    if unknown:
        raise SystemExit(f"error: {ASSIGNED_PATH.name} names categories no reply maps to: {unknown}")
    return rows


def counts_from_replies(contributors: int) -> list:
    """(category, n, assigned) from the replies and the assigned file, "Not yet
    reported" filling up to the contributors; largest first, ties alphabetical,
    "Not yet reported" last, empty categories left out."""
    replied = Counter(read_replies())
    assigned = Counter()
    for category, k in read_assigned():
        assigned[category] += k
    known = sum(replied.values()) + sum(assigned.values())
    if known > contributors:
        raise SystemExit(f"error: {known} disciplines for {contributors} contributors")
    rows = [(c, replied[c] + assigned[c], assigned[c]) for c in set(replied) | set(assigned)]
    rows = sorted((r for r in rows if r[1] > 0), key=lambda r: (-r[1], r[0]))
    if contributors > known:
        rows.append((NOT_REPORTED, contributors - known, 0))
    return rows


def byline_source() -> str:
    raise SystemExit("error: the byline check needs the manuscript, which the release "
                     "does not ship; the deposit carries the counts, so run --from-counts")


NOT_REPORTED = "Not yet reported"
FINAL_PANEL = 41     # complete Round 4 responses, the panel


ASSIGNED_SENTENCE = ("Of the {n}, {reported} reported their discipline, and the study team assigned "
                     "the other {assigned} from public profiles and publication records.")


def build_table(counts: list) -> str:
    """The table from (category, n) or (category, n, assigned) rows, with "Not
    yet reported" kept last. Once every contributor has a discipline, the
    caption says how many reported it and how many the study team assigned
    (CH-73). While replies are missing the caption carries a preliminary
    marker with the replies so far, which leaves the assigned disciplines out."""
    n = sum(row[1] for row in counts)
    missing = sum(row[1] for row in counts if row[0] == NOT_REPORTED)
    assigned = sum(row[2] for row in counts if len(row) > 2)
    reported = n - missing - assigned
    counts = [c for c in counts if c[0] != NOT_REPORTED] + [c for c in counts if c[0] == NOT_REPORTED]
    body = "\n".join(f"{tex(row[0])} & {row[1]} & {100 * row[1] / n:.0f} \\\\" for row in counts)
    note = ""
    if assigned and not missing:
        note = " " + ASSIGNED_SENTENCE.format(n=n, reported=reported, assigned=assigned)
    if missing:
        note += f" \\pending{{WIP: preliminary, {reported} of {n} replies so far}}"
    return (
        "% Auto-generated by scripts/contributor_table.py -- do not edit by hand.\n"
        "\\begin{table}[!htbp]\n\\centering\n"
        f"\\caption{{\\textbf{{Primary discipline of the contributors.}} "
        f"The {n} contributors are everyone outside the study team who took part in at least "
        f"one Delphi round. They are a wider group than the {FINAL_PANEL} Round~4 panellists, "
        f"whose disciplines the anonymous final round did not record.{note}}}\n"
        "\\label{tab:contributor_disciplines}\n"
        "\\begin{tabular}{@{}l r r@{}}\n\\toprule\n"
        "Discipline & $n$ & \\% \\\\\n\\midrule\n"
        f"{body}\n\\midrule\nTotal & {n} & 100 \\\\\n"
        "\\bottomrule\n\\end{tabular}\n\\end{table}\n"
    )


def tex(s: str) -> str:
    return s.replace("&", r"\&").replace("%", r"\%")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--init", action="store_true", help="write the CSV with names only")
    mode.add_argument("--from-counts", action="store_true",
                      help=f"write the table from {COUNTS_PATH.name} alone, without the "
                           "per-name file or the byline check")
    mode.add_argument("--from-replies", action="store_true",
                      help=f"write {COUNTS_PATH.name} and the table from {REPLIES_PATH.name} "
                           f"and {ASSIGNED_PATH.name}")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # names carry accents

    if args.from_counts:
        counts = read_counts()
        TABLE_OUT.parent.mkdir(parents=True, exist_ok=True)
        TABLE_OUT.write_text(build_table(counts), encoding="utf-8")
        print(f"wrote {TABLE_OUT} from {COUNTS_PATH.name}: "
              f"{sum(row[1] for row in counts)} contributors in {len(counts)} categories")
        return

    if args.from_replies:
        contributors = len(panel(byline_source())[0])
        counts = counts_from_replies(contributors)
        table = build_table(counts)
        write_counts(counts)
        TABLE_OUT.parent.mkdir(parents=True, exist_ok=True)
        TABLE_OUT.write_text(table, encoding="utf-8")
        for category, k, assigned in counts:
            print(f"  {category}: {k}" + (f" ({assigned} assigned)" if assigned else ""))
        print(f"wrote {COUNTS_PATH}\nwrote {TABLE_OUT}: {contributors} contributors, "
              f"{len(read_replies())} replies, {sum(row[2] for row in counts)} assigned")
        return

    members, names = panel(byline_source())
    not_panel = [a for a in names if a not in members]
    not_author = [m for m in members if m not in names]
    print(f"authors {len(names)}, panellists {len(members)}")
    print(f"  authors not on the panel: {', '.join(not_panel)}")
    print(f"  panellists who are not authors: {', '.join(not_author)}")

    if args.init:
        if CSV_PATH.exists():
            raise SystemExit(f"error: {CSV_PATH} exists; --init never overwrites it")
        CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CSV_PATH.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(FIELDS)
            w.writerows([m, "", ""] for m in members)
        print(f"wrote {CSV_PATH} with {len(members)} names")
        return

    rows = read_csv()
    listed = [r["name"] for r in rows]
    if sorted(listed) != sorted(members):
        raise SystemExit("error: disciplines.csv does not match the byline note\n"
                         f"  missing: {sorted(set(members) - set(listed))}\n"
                         f"  extra:   {sorted(set(listed) - set(members))}")
    counts = count_categories(rows)
    write_counts(counts)
    TABLE_OUT.write_text(build_table(counts), encoding="utf-8")
    assigned = sum(1 for r in rows if (r["category"] or "").strip())
    print(f"wrote {COUNTS_PATH}")
    print(f"wrote {TABLE_OUT}: {assigned} of {len(rows)} panellists have a category")


if __name__ == "__main__":
    main()

"""
Round 4 stage 1: Extract the LimeSurvey CSV export into an anonymized JSON
structure compatible with the existing qualitative analysis scripts.

The output mirrors the Round 3 `extracted_responses.json` schema
(`submissions[].open_ended_comments`, `submissions[].section_f_questions`) so
scripts 5-8 can consume it unchanged, and adds Round 4-specific fields:
per-statement ratings (distinguishing the "Not qualified to respond" code from
blanks), Section E rankings, and coarse demographics.

Per the pre-registration, partial completions are retained for the statements a
panelist actually rated (any row with >=1 genuine 1-6 rating, or a non-empty
submit date), and each submission is tagged `complete`/`partial` with its
`last_page` and `n_ratings`. Downstream consensus and ranking stats are already
per-statement / per-respondent, so they consume these unchanged.

Column positions are taken from R4/DELPHI analysis/survey_783452_R_syntax_file.R
(1-based there; 0-based here).
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import ROUND4_CSV, ROUND4_RESPONSES, NOT_QUALIFIED_CODE
from r4_statements import (
    R4_STATEMENTS,
    SECTION_COMMENT_VARS,
    E_PHASES,
    F_QUESTIONS,
    CSV_VAR_TO_F_ID,
)

# ---------------------------------------------------------------------------
# Column indices (0-based) from the R syntax file.
# ---------------------------------------------------------------------------
COL_SUBMITDATE = 1
COL_LASTPAGE = 2

# Rating columns, in canonical statement order, mapped to R4 ids.
RATING_COLS = {}
for idx, sid in zip(range(25, 38), [s for s in R4_STATEMENTS if s.startswith("A")]):
    RATING_COLS[idx] = sid
for idx, sid in zip(range(39, 47), [s for s in R4_STATEMENTS if s.startswith("B")]):
    RATING_COLS[idx] = sid
for idx, sid in zip(range(48, 58), [s for s in R4_STATEMENTS if s.startswith("C")]):
    RATING_COLS[idx] = sid
for idx, sid in zip(range(59, 68), [s for s in R4_STATEMENTS if s.startswith("D")]):
    RATING_COLS[idx] = sid

SECTION_COMMENT_COLS = {"A": 38, "B": 47, "C": 58, "D": 68}

# Section E ranking columns: phase -> list of 7 column indices (rank 1..7).
RANKING_COLS = {
    "E01": list(range(69, 76)),
    "E02": list(range(76, 83)),
    "E03": list(range(83, 90)),
}

# Section F open-ended columns: F01..F07.
SECTION_F_COLS = {f"F0{i}": 89 + i for i in range(1, 8)}  # F01->90 ... F07->96

# Demographic columns -> (field name, code->label map).
REGION = {"A1": "Europe", "A2": "North America", "A3": "Latin America & Caribbean",
          "A4": "Asia-Pacific", "A5": "South Asia", "A6": "Middle East & North Africa",
          "A7": "Sub-Saharan Africa", "A8": "Oceania"}
BACKGROUND = {"A1": "Academic / Researcher", "A2": "Clinician / Practitioner",
              "A3": "Public health / Policy / Government", "A4": "Industry / Private sector",
              "A5": "Regulatory affairs", "A6": "NGO / Non-profit",
              "A7": "Patient / Lived experience representative"}
EXPERIENCE = {"A1": "Less than 5 years", "A2": "5 to 10 years",
              "A3": "11 to 20 years", "A4": "More than 20 years"}
POSITION = {"A1": "PhD candidate / Doctoral researcher", "A2": "Postdoctoral researcher",
            "A3": "Assistant Professor / Junior faculty / Lecturer",
            "A4": "Associate Professor / Senior lecturer",
            "A5": "Full Professor / Senior researcher", "A6": "Emeritus / Retired",
            "A7": "Non-academic professional (clinical, policy, industry)"}
EXPERTISE = {"A1": "No significant experience in this field",
             "A2": "Some experience, but limited depth",
             "A3": "Substantial experience in this field",
             "A4": "Extensive experience and active involvement",
             "A5": "Recognized expert with leadership in this field"}
SECTOR = {"A1": "University / Research institute", "A2": "Hospital / Health system",
          "A3": "Government / Public agency", "A4": "International organization (e.g., WHO, ECDC)",
          "A5": "NGO / Non-profit", "A6": "Private industry",
          "A7": "Independent practice / Self-employed"}
PUBLICATIONS = {"1": "Yes", "2": "No"}

# (col, code->label map, free-text "Other" column or None). Background, position
# and sector each have a LimeSurvey "Other" (-oth-) option with a free-text box.
DEMOGRAPHIC_COLS = {
    "region": (7, REGION, None),
    "background": (16, BACKGROUND, 17),
    "experience": (18, EXPERIENCE, None),
    "position": (19, POSITION, 20),
    "expertise": (21, EXPERTISE, None),
    "sector": (22, SECTOR, 23),
    "publications": (24, PUBLICATIONS, None),
}

# Free-text "Other" demographic answers are recoded to a canonical category when
# the intent is unambiguous; otherwise they surface as "Other: <text>" rather than
# being silently dropped to None. Keyed on (field, lower-cased free text) so the
# rule re-applies to any dataset (the extract is anonymized and cannot key on a
# response id). Each entry records a free-text value seen in the data and the
# canonical category it maps to.
OTHER_NORMALIZATION = {
    ("background", "phd student"): "Academic / Researcher",
}


def _decode_demographic(field: str, row: list, col: int, mapping: dict, other_col):
    """Decode a demographic code, handling the LimeSurvey 'Other' (-oth-) option.

    Blank -> None; a normal code -> its label; an 'Other' answer -> the canonical
    category from OTHER_NORMALIZATION when known, else 'Other: <free text>' so it
    is never silently lost from the panel breakdown.
    """
    code = (row[col] or "").strip()
    if not code:
        return None
    if code == "-oth-":
        text = (row[other_col] or "").strip() if other_col is not None else ""
        canonical = OTHER_NORMALIZATION.get((field, text.lower()))
        if canonical:
            return canonical
        return f"Other: {text}" if text else "Other"
    return mapping.get(code)


def _parse_rating(cell: str):
    """Return (rating_1_6_or_None, not_qualified_bool)."""
    cell = (cell or "").strip()
    if not cell:
        return None, False
    try:
        code = int(cell)
    except ValueError:
        return None, False
    if code == NOT_QUALIFIED_CODE:
        return None, True
    if 1 <= code <= 6:
        return code, False
    return None, False


def extract(csv_path: Path = None, output_file: Path = None):
    csv_path = csv_path or ROUND4_CSV
    output_file = output_file or ROUND4_RESPONSES

    if not csv_path.exists():
        raise FileNotFoundError(f"Round 4 CSV not found at {csv_path}")

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))

    header, data_rows = rows[0], rows[1:]

    # Pre-registration: "Partial completions (where a panelist rates some but not
    # all statements) will be included for the statements that were rated." So we
    # keep every row that contributed at least one genuine 1-6 rating, plus any
    # formally completed row (non-empty submit date). Pure abandons (nothing rated)
    # add no data and are skipped. Each kept submission is tagged complete/partial
    # so downstream reporting can pick the right denominator.
    submissions = []
    n_complete = 0
    n_partial = 0
    fingerprints = {}  # coarse demographic fingerprint -> [last_page,...] (dup guard)
    for row in data_rows:
        # Per-statement ratings (anonymized: no id/date/seed/timing retained).
        feedback = []
        n_ratings = 0
        for idx, sid in RATING_COLS.items():
            rating, not_qualified = _parse_rating(row[idx])
            if rating is not None:
                n_ratings += 1
            feedback.append({
                "statement_id": sid,
                "section": R4_STATEMENTS[sid]["section"],
                "rating": rating,
                "not_qualified": not_qualified,
            })

        has_submitdate = len(row) > COL_SUBMITDATE and bool(row[COL_SUBMITDATE].strip())
        if not has_submitdate and n_ratings == 0:
            continue  # no submit date and nothing rated -> contributes no data

        # Section-level free text -> open_ended_comments keyed as "Section X"
        # (matching the Round 3 convention so scripts 5/6 consume it unchanged).
        open_ended_comments = {}
        for section, col in SECTION_COMMENT_COLS.items():
            text = (row[col] or "").strip()
            if text:
                open_ended_comments[f"Section {section}"] = text

        # Section F -> list compatible with scripts 7/8.
        section_f_questions = []
        for var, col in SECTION_F_COLS.items():
            response = (row[col] or "").strip()
            qid = CSV_VAR_TO_F_ID[var]
            section_f_questions.append({
                "question_id": qid,
                "question_text": F_QUESTIONS[qid],
                "response": response,
            })

        # Section E rankings: phase -> [item_code at rank1, rank2, ...] (None if blank).
        rankings = {}
        for phase, cols in RANKING_COLS.items():
            ordered = []
            for col in cols:
                cell = (row[col] or "").strip()
                ordered.append(int(cell) if cell.isdigit() else None)
            rankings[phase] = ordered

        demographics = {
            field: _decode_demographic(field, row, col, mapping, other_col)
            for field, (col, mapping, other_col) in DEMOGRAPHIC_COLS.items()
        }

        last_page_raw = row[COL_LASTPAGE].strip() if len(row) > COL_LASTPAGE else ""
        complete = has_submitdate
        if complete:
            n_complete += 1
        else:
            n_partial += 1

        # Coarse-demographic fingerprint (region, country, background, experience,
        # position, expertise, sector, publications) to flag un-merged repeat
        # attempts by the same panelist, which would double-count ratings. This is
        # only a heuristic: distinct senior experts can share a coarse fingerprint
        # (several do among the completed responses), so we warn only when a group
        # contains a partial (the case that actually needs merge verification).
        fp = tuple((row[c] or "").strip() for c in (7, 8, 16, 18, 19, 21, 22, 24))
        if any(fp):
            fingerprints.setdefault(fp, []).append((last_page_raw or "?", complete))

        submissions.append({
            "complete": complete,
            "last_page": int(last_page_raw) if last_page_raw.isdigit() else None,
            "n_ratings": n_ratings,
            "feedback": feedback,
            "open_ended_comments": open_ended_comments,
            "section_f_questions": section_f_questions,
            "rankings": rankings,
            "demographics": demographics,
        })

    output = {
        "metadata": {
            "round": 4,
            "n_participants": len(submissions),
            "n_complete": n_complete,
            "n_partial": n_partial,
            "anonymized": True,
            "source": csv_path.name,
            "inclusion": "Per pre-registration, partial completions are included for "
                         "the statements they rated; per-statement n therefore varies. "
                         "n_participants counts all included submissions (complete + partial).",
            "rating_scale": "1-6 agreement (completely disagree..completely agree); "
                            "code 7 = 'Not qualified to respond' (excluded from statistics)",
            "section_e_phases": E_PHASES,
        },
        "submissions": submissions,
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    # ensure_ascii=True (the default) keeps the file pure ASCII, matching the
    # Round 3 extract and ensuring it loads regardless of platform default
    # encoding (the reused scripts 5-8 open it without specifying UTF-8).
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    # --- sanity checks -----------------------------------------------------
    n = len(submissions)
    for s in submissions:
        assert len(s["feedback"]) == 40, "Each submission must have 40 statement ratings"
    n_nq = sum(1 for s in submissions for fb in s["feedback"] if fb["not_qualified"])
    n_blank = sum(1 for s in submissions for fb in s["feedback"]
                  if fb["rating"] is None and not fb["not_qualified"])

    print(f"[OK] Extracted {n} submissions ({n_complete} complete, {n_partial} partial) "
          f"x 40 statements -> {output_file}")
    print(f"     'Not qualified' abstentions: {n_nq}; blank/missing ratings: {n_blank}")

    # Warn (non-fatal) about a coarse fingerprint shared by >1 submission *when at
    # least one is partial*: that is the case that may be the same panelist's
    # un-merged repeat attempt and must be verified/de-duplicated upstream to avoid
    # double-counting (per-statement inclusion assumes one submission per panelist).
    # All-complete collisions are left unflagged: distinct experts share fingerprints.
    dups = {fp: entries for fp, entries in fingerprints.items()
            if len(entries) > 1 and any(not c for _, c in entries)}
    if dups:
        print(f"     [WARN] {len(dups)} fingerprint(s) shared by a partial + other "
              f"submission(s) - verify these are not un-merged repeat attempts:")
        for fp, entries in dups.items():
            tag = ", ".join(f"page {p}{'' if c else '*'}" for p, c in entries)
            print(f"            region={fp[0]} country={fp[1]} bg={fp[2]} exp={fp[3]} "
                  f"pos={fp[4]} exq={fp[5]} sec={fp[6]} pub={fp[7]} | {tag}  (*=partial)")
    return output


if __name__ == "__main__":
    extract()

"""Paths and analysis constants for the Round 4 Delphi pipeline."""
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
#
# data/ mirrors the deposit exactly, so replication is "unpack the deposit into
# data/" with no rearranging. Two of the three folders are what you downloaded
# and the third is what this code writes:
#
#   data/delphi/      survey exports and Round 3 artifacts, from the deposit
#   data/literature/  screening results and hand labels, from the deposit
#   data/generated/   everything the pipeline produces
#
# Keeping output out of the first two means the deposit copy stays pristine and
# `rm -rf data/generated` is a complete clean.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent  # Go up from scripts to project root
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DATA_DIR = PROJECT_ROOT / "data"
DELPHI_DIR = DATA_DIR / "delphi"
LITERATURE_DIR = DATA_DIR / "literature"
GENERATED_DIR = DATA_DIR / "generated"
TABLES_DIR = PROJECT_ROOT / "tables"
FIGURES_DIR = PROJECT_ROOT / "figures"

for dir_path in [GENERATED_DIR, TABLES_DIR, FIGURES_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Inputs, unpacked from the data deposit.
ROUND4_RAW_EXPORT = DELPHI_DIR / "round4_raw_export.csv"
ROUND4_MERGED_RECORD = DELPHI_DIR / "round4_merged_record.csv"
LITERATURE_CSV = LITERATURE_DIR / "articles-full-screen-results.csv"

# The single Round 3 artifact the Round 4 comparison reads (READ-ONLY) to
# recompute Round 3 median/IQR from the stored rating distributions.
ROUND3_STATEMENT_ANALYSES = DELPHI_DIR / "round3_statement_analyses.json"

# Generated. r4_build_dataset.py writes the analysis dataset from the two raw
# files above, and the pipeline stages write the rest.
ROUND4_CSV = GENERATED_DIR / "round4_dataset.csv"
ROUND4_RESPONSES = GENERATED_DIR / "round4_responses.json"
ROUND4_REPORTS_DIR = GENERATED_DIR / "reports"

# Kept so existing call sites read unchanged.
ROUND4_RAW_DIR = DELPHI_DIR
ROUND4_EXTRACTED_DIR = GENERATED_DIR
ROUND4_ANALYSIS_DIR = GENERATED_DIR
RAW_DATA_DIR = DELPHI_DIR
EXTRACTED_DATA_DIR = GENERATED_DIR
ANALYSIS_DIR = GENERATED_DIR
STATEMENTS_ANALYSIS_DIR = DELPHI_DIR
CONSOLIDATED_DIR = GENERATED_DIR

# LimeSurvey rating coding: 1-6 = agreement scale, 7 = "Not qualified to
# respond" (an abstention that must be excluded from all statistics).
NOT_QUALIFIED_CODE = 7

# A-priori consensus thresholds, based on dispersion (IQR) on the 6-point scale.
# See the Methods, "Rating and consensus".
CONSENSUS_IQR_MAX = 1.0        # IQR <= 1.0          -> consensus
NEAR_CONSENSUS_IQR_MAX = 1.5   # 1.0 < IQR <= 1.5    -> near-consensus
                               # IQR > 1.5           -> non-consensus

# Round 3 -> Round 4 stability thresholds (descriptive). A statement is stable
# if its median shifts by less than STABILITY_MEDIAN_MAX scale points AND its
# IQR shifts by less than STABILITY_IQR_MAX.
STABILITY_MEDIAN_MAX = 1.0
STABILITY_IQR_MAX = 0.5

# Data Processing Configuration
ANONYMIZE_PARTICIPANTS = True  # Strip all participant IDs from output

# Rating Scale
RATING_SCALE_MIN = 1
RATING_SCALE_MAX = 6

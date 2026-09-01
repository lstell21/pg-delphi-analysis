"""
Round 4 statement registry and Round 3 -> Round 4 crosswalk.

Single source of truth for:
  * the 40 finalized Round 4 statements (id -> section, full text, short label),
  * the Section E ranking items and phases,
  * the Section F open-ended questions,
  * the Round 3 -> Round 4 statement crosswalk used by the comparison.

All statement texts are transcribed verbatim from the LimeSurvey-generated
`variable.labels` in R4/DELPHI analysis/survey_783452_R_syntax_file.R.

Crosswalk note: between Round 3 and Round 4 two pairs of statements were merged
(see the Results): Round 3 A-2 + A-3 -> Round 4 A02, and Round 3
C-6 + C-11 -> Round 4 C06. All other statements map 1:1 (with the Section A
index shifting by one after the A02 merge).
"""

# ---------------------------------------------------------------------------
# Round 4 statements: id -> {section, text, short_label}
# Column numbers refer to the R syntax file for traceability.
# ---------------------------------------------------------------------------
R4_STATEMENTS = {
    # Section A: Model Design & Complexity (cols 26-38)
    "A01": {
        "section": "A",
        "short_label": "Model quality depends on the question",
        "text": "The suitability of an epidemiological model depends on the question it addresses, although certain quality criteria, such as mathematical correctness, reproducibility, and transparency, apply regardless of the specific research question.",
    },
    "A02": {
        "section": "A",
        "short_label": "No single model; adapt and extend existing models",
        "text": "There is no single model that fits all scenarios. A limited set of well-developed models can address multiple questions, and existing models can often be adapted or extended in crisis situations rather than requiring an entirely new model for each question, provided adequate data are collected.",
    },
    "A03": {
        "section": "A",
        "short_label": "Integrating diverse models deepens insight",
        "text": "We gain deeper insights by integrating diverse models that differ in structure, assumptions, and methodological techniques. Convergence on similar results across independently constructed models increases robustness and plausibility, while divergences illuminate uncertainty, reveal hidden assumptions, and identify areas requiring further investigation.",
    },
    "A04": {
        "section": "A",
        "short_label": "Simple models can inform policymakers",
        "text": "In favorable conditions, simple models can illuminate core mechanisms and inform policymakers about future developments, potential mitigations, and their effectiveness and costs. Their simplifying assumptions and boundary conditions should be clearly communicated to policymakers to avoid misinterpretations, and they should be complemented by more complex analyses when needed.",
    },
    "A05": {
        "section": "A",
        "short_label": "Speed and uncertainty in rapid response",
        "text": "During pandemics driven by fast-spreading diseases, speed is essential to provide timely insights that support rapid decision-making. Rapid-response modeling should be accompanied by clear communication of uncertainties and caveats, at minimum qualitatively. Formal uncertainty quantification should be pursued where feasible.",
    },
    "A06": {
        "section": "A",
        "short_label": "Complexity vs. completeness trade-off",
        "text": "There is a trade-off between model complexity and completeness, so simplifying assumptions should not omit factors critical to the specific question. Sensitivity analysis should be used to determine which simplifications are acceptable.",
    },
    "A07": {
        "section": "A",
        "short_label": "Iterative model development",
        "text": "Model development should follow an iterative approach with regular evaluation processes, recognizing that not all factors are known at the outset and that requirements may evolve as data accumulate. The pace of model updates should be adapted to the context and urgency of the situation.",
    },
    "A08": {
        "section": "A",
        "short_label": "Parameter identifiability",
        "text": "Managing many parameter combinations in complex models poses significant challenges. When the number of parameters to be estimated exceeds what the available data can support, identifiability becomes a problem, making reliable estimation difficult.",
    },
    "A09": {
        "section": "A",
        "short_label": "Simplified models clarify mechanisms",
        "text": "Simplified models that focus on key parameters can clarify specific mechanisms when their scope and limitations are made explicit. Where feasible, their outputs should be compared with empirical data and, when available, with more comprehensive frameworks.",
    },
    "A10": {
        "section": "A",
        "short_label": "Integrating socio-economic & behavioral factors",
        "text": "Integrating socio-economic and behavioral factors into epidemiological models can be essential for capturing real-world transmission dynamics and intervention effects, and their inclusion should be justified based on the question being addressed. Doing so, however, increases data and calibration demands, and reliable behavioral data remain scarce, requiring careful validation to balance explanatory richness with predictive reliability.",
    },
    "A11": {
        "section": "A",
        "short_label": "Agent-based models",
        "text": "Agent-based models offer high-resolution modeling of population heterogeneity and spatial dynamics that are difficult to capture with standard compartmental models. They require more setup, calibration, and computational resources. While they can be used for short-term prediction, their particular strength lies in exploring intervention scenarios and system behavior under policy changes. Hybrid approaches combining compartmental and agent-based elements may also be considered.",
    },
    "A12": {
        "section": "A",
        "short_label": "Models to support government advice",
        "text": "To support government advice during a pandemic, models should be informed by the best available data on the epidemic state and virus variants to predict policy-relevant outcomes including case numbers, hospitalizations, and deaths. They should incorporate behavioral factors where they influence transmission and consider economic and psychological effects when they meaningfully influence policy decisions. The scope of models should be matched to the decision context and available data.",
    },
    "A13": {
        "section": "A",
        "short_label": "Explicit calibration reporting",
        "text": "Calibration reporting should be explicit, including which calibration method was used, which parameters were estimated, data sources, assumptions, and the associated uncertainties, to support reproducibility and understanding of model performance.",
    },
    # Section B: Data Availability & Quality (cols 40-47)
    "B01": {
        "section": "B",
        "short_label": "Timely data availability",
        "text": "Timely data availability is important for effective modeling and decision support. When quality trade-offs are necessary, document how data limitations influence model outputs and clearly communicate uncertainties to decision-makers. In rapid decision settings, preliminary data or best estimates may be used, but analyses should explicitly state the uncertainties and caveats.",
    },
    "B02": {
        "section": "B",
        "short_label": "Open sharing (FAIR principles)",
        "text": "Open sharing of models, data, and code, along with uncertainties and assumptions, in line with the FAIR (and FAIR4RS) principles, both within the scientific community and with policymakers, improves trust, reproducibility, and the practical uptake of model results.",
    },
    "B03": {
        "section": "B",
        "short_label": "Limits of open sharing; share aggregate by default",
        "text": "Open sharing has limitations, including privacy concerns, particularly for individual-level data, which can be mitigated by data access agreements or synthetic data. Aggregate-level data (e.g., hospital admissions, bed occupancy) generally poses minimal privacy risk and should be shared openly by default. These frameworks should be established in advance of emergencies.",
    },
    "B04": {
        "section": "B",
        "short_label": "Socio-behavioral data alongside clinical surveillance",
        "text": "Socio-behavioral data collection should be integrated alongside clinical surveillance from the outset, with the scope adapted to the pathogen and transmission context. Data privacy protections should balance emergency data-sharing needs.",
    },
    "B05": {
        "section": "B",
        "short_label": "Non-traditional data sources",
        "text": "Non-traditional data sources, such as digital platforms, mobility tracking, search queries, and participatory surveillance, can complement conventional surveillance and should be considered from the outset, with appropriate privacy safeguards.",
    },
    "B06": {
        "section": "B",
        "short_label": "Sentinel surveillance vs. representative surveys",
        "text": "Sentinel surveillance and population-representative surveys have complementary goals and both are needed. The choice between them should depend on the specific modeling question.",
    },
    "B07": {
        "section": "B",
        "short_label": "Multiple sampling approaches",
        "text": "Multiple sampling approaches are needed for comprehensive surveillance. Community-based sampling can provide timely prevalence data, while hospital-based sampling, though biased for population prevalence estimation, is valuable for understanding disease severity and health system burden. Wastewater surveillance can provide privacy-preserving, complementary data. All data sources carry inherent biases that should be transparently characterized and accounted for in analysis.",
    },
    "B08": {
        "section": "B",
        "short_label": "Ethical frameworks for data inequity",
        "text": "Ethical frameworks should explicitly address inequity in data collection and access to benefits. Data privacy protections should balance emergency data-sharing needs, and predefined ethical safeguards should be established prior to a pandemic.",
    },
    # Section C: Uncertainty, Validation & Communication (cols 49-58)
    "C01": {
        "section": "C",
        "short_label": "Context for model outputs; uncertainty as ranges",
        "text": "It is important to provide context for model outputs, including estimates of uncertainty, key assumptions, and the decisions the model is intended to inform. Not all models include formal uncertainties; when they exist, report them as ranges rather than precise values to avoid implying false precision.",
    },
    "C02": {
        "section": "C",
        "short_label": "Specify and quantify uncertainty types",
        "text": "Uncertainty arising from model structure, assumptions, and data should be clearly specified and, where possible, quantified. It is important to specify the types of uncertainty that matter, such as parameter uncertainty, data uncertainty, and uncertainty from model assumptions. Uncertainty should be communicated alongside model results and linked to the model's intended use, clarifying which decisions it supports and how robust those conclusions are.",
    },
    "C03": {
        "section": "C",
        "short_label": "Forecasts vs. scenarios",
        "text": "Forecasts and scenarios carry different forms of uncertainty and should be communicated differently. Forecasts involve predictive uncertainty about what will happen, while scenarios explore what could happen under specified assumptions. These represent points on a continuum rather than a strict dichotomy.",
    },
    "C04": {
        "section": "C",
        "short_label": "Validation distinct from calibration",
        "text": "Model validation should be clearly distinguished from calibration and verification, with validation defined as testing model performance on data not used for fitting, where feasible. Projections should not be assumed to be stable over time; validation processes should be continually updated with emerging empirical data, using adaptive criteria to guide when and how to update models.",
    },
    "C05": {
        "section": "C",
        "short_label": "Transparent sensitivity analyses",
        "text": "Sensitivity analyses regarding parameter choices and the omission of potential other factors should be conducted with transparent methods and clearly justified parameter ranges. Initial criteria should be specified where possible but should be revisable as understanding evolves. Results should accompany all policy-informing model outputs and be communicated in accessible, decision-relevant formats.",
    },
    "C06": {
        "section": "C",
        "short_label": "Interactive visualization tools & dashboards",
        "text": "Interactive visualization tools and dynamic dashboards can improve comprehension of model scenarios and limitations, but their design should be tailored to the intended audience, with attention to the risks of oversimplification and misinterpretation. They should be co-developed with users to ensure relevance and usability, regularly updated to reflect new evidence, and designed to make assumptions and uncertainties transparent. Adequate resources must be allocated for development and maintenance.",
    },
    "C07": {
        "section": "C",
        "short_label": "Stable, well-documented data formats & APIs",
        "text": "Data formats and APIs should change only when necessary to capture new epidemiological variables or phenomena. When changes occur, they should be managed responsibly with clear documentation, versioning, and backward compatibility where feasible.",
    },
    "C08": {
        "section": "C",
        "short_label": "Free API access; machine-readable data",
        "text": "Public data websites should offer free API access, and the underlying raw or processed data should be published alongside visualizations in a machine-readable format such as CSV or JSON. When data cannot be publicly released for privacy or legal reasons, de-identified or aggregated data should be provided in a machine-readable format, accompanied by metadata and documentation to enable reuse and reproducibility.",
    },
    "C09": {
        "section": "C",
        "short_label": "Policymaker understanding of uncertainty",
        "text": "Policymakers do not need technical modeling expertise, but should have a foundational understanding of model uncertainty and its implications to ensure policies align with scientific evidence. The primary responsibility for making uncertainty accessible lies with modelers and scientists, who should communicate it in accessible terms to non-expert audiences. Engaging policymakers early helps tailor how uncertainty is presented and what information is most useful for decision-making.",
    },
    "C10": {
        "section": "C",
        "short_label": "Communicate to public and media",
        "text": "Communication strategies for model results should address not only policymakers but also the general public and media, as public trust in modeling was a critical challenge during COVID-19.",
    },
    # Section D: Collaboration, Interdisciplinarity & Ethics (cols 60-68)
    "D01": {
        "section": "D",
        "short_label": "Long-term interdisciplinary collaboration",
        "text": "Effective pandemic preparedness requires long-term, interdisciplinary collaboration among disciplines, including epidemiologists, clinicians, virologists, microbiologists, systems engineering and operational research experts, mathematicians, statisticians, computer and data scientists, physicists, social scientists, economists, behavioral scientists, public health practitioners, and others.",
    },
    "D02": {
        "section": "D",
        "short_label": "Global cooperation & capacity-building",
        "text": "Global modeling cooperation should be strengthened through joint platforms (modeling hubs, joint forecasting and scenario efforts) and capacity-building in LMICs and under-resourced settings. It should be supported by baseline funding for collaboration between public health institutes and academia, and by project funding to drive innovation in modeling.",
    },
    "D03": {
        "section": "D",
        "short_label": "Cross-border data-sharing agreements",
        "text": "Cross-border data-sharing agreements should be developed and strengthened to address feasibility constraints such as data protection policies, geopolitical issues, and other barriers.",
    },
    "D04": {
        "section": "D",
        "short_label": "Dedicated communication roles",
        "text": "Dedicated communication roles, with appropriate training in bridging scientific and policy communication, can serve as mediators between scientific modeling teams, policymakers, the media, and the general public to reduce misinterpretation and increase policy uptake.",
    },
    "D05": {
        "section": "D",
        "short_label": "Ethics embedded upstream",
        "text": "Ethical considerations should be embedded upstream into model development, validation, and scenario communication. They should explicitly address how modeling choices influence resource allocation decisions and affect vulnerable groups. The depth of ethical review should be proportionate to the decision context and urgency.",
    },
    "D06": {
        "section": "D",
        "short_label": "Identify and mitigate biases",
        "text": "Biases related to socio-economic status, structural disadvantage, and marginalized communities should be identified and mitigated. A flexible ethical framework for guiding pandemic modeling should be developed during preparedness phases, with the understanding that it will need to be adapted as pandemic-specific challenges emerge.",
    },
    "D07": {
        "section": "D",
        "short_label": "Well-being of children & vulnerable groups",
        "text": "The well-being of children and other vulnerable groups matters. Children often lack a strong advocacy voice, and their needs and interests are at times overlooked. Models informing pandemic policy should explicitly consider age-stratified impacts across vulnerable populations, recognizing that many interventions can support both infection control and continuity of education simultaneously.",
    },
    "D08": {
        "section": "D",
        "short_label": "Lived experience of affected communities",
        "text": "There is value in incorporating the lived experience of affected communities into policy making and pandemic response decisions. This should be achieved through concrete mechanisms such as community advisory boards or structured consultation, established during preparedness phases.",
    },
    "D09": {
        "section": "D",
        "short_label": "Institutional support for science communication",
        "text": "Good science communication should be supported by institutions and public funding, rather than resting solely on individual scientists. Structured exchange between science journalists and modelers can improve accuracy and policy relevance and should be encouraged, with science journalism striving to avoid sensationalism and misinformation.",
    },
}

# Mapping from the rated CSV column variable name (R syntax) to the R4 id.
# Section A/B/C/D rating columns are named like "A01_SQ001", "B01_SQ001", ...
CSV_VAR_TO_R4_ID = {f"{sid}_SQ001": sid for sid in R4_STATEMENTS}

# Sentence case, matching SECTION_TITLES in main_text_tables.py and the section
# names as the article's prose gives them. Kept in one case everywhere so the
# same four sections do not read as two different sets of names.
SECTION_NAMES = {
    "A": "Model design and complexity",
    "B": "Data availability and quality",
    "C": "Uncertainty, validation, and communication",
    "D": "Collaboration, interdisciplinarity, and ethics",
}

# Section comment fields (one free-text field per section) -> CSV variable name.
SECTION_COMMENT_VARS = {"A": "A14", "B": "B09", "C": "C11", "D": "D10"}

# ---------------------------------------------------------------------------
# Section E: ranking task (7 items ranked across 3 phases)
# ---------------------------------------------------------------------------
E_ITEMS = {
    1: "Real-time data-sharing systems.",
    2: "Development of rapid-response modeling teams.",
    3: "Definition and usage of standardized modeling protocols.",
    4: "Enhanced validation of models with empirical data.",
    5: "Greater inclusion of socio-behavioral sciences in models.",
    6: "Improved science communication tools (e.g., interactive dashboards, uncertainty visualizations) for policymakers.",
    7: "Ethical frameworks for decision-making based on model outcomes.",
}

E_PHASES = {
    "E01": "Before an epidemic or pandemic emerges",
    "E02": "During the early stage of emergence",
    "E03": "After the event, in preparation for potential future pandemics",
}

# ---------------------------------------------------------------------------
# Section F: open-ended questions (ids use the R3 "F-n" convention so the
# existing Section F analysis/report scripts consume them unchanged).
# ---------------------------------------------------------------------------
F_QUESTIONS = {
    "F-1": "What is the single most important lesson from past pandemic modeling for future pandemics?",
    "F-2": "In hindsight, what was the most important aspect of the COVID-19 pandemic that most models failed to address?",
    "F-3": "People trust model predictions across many aspects of their everyday lives (e.g., weather forecasts). Why did many fail to trust the outcomes of epidemiological modeling during the pandemic?",
    "F-4": "What is the biggest gap currently limiting the effectiveness of infectious disease modeling?",
    "F-5": "Which interdisciplinary collaborations are most urgently needed to improve pandemic modeling?",
    "F-6": "How can model outcomes be more effectively integrated into policy decisions?",
    "F-7": "What key ethical issues must pandemic modelers address to enhance the implementation of policy?",
}

# CSV variable name (F01..F07) -> F-n question id.
CSV_VAR_TO_F_ID = {f"F0{i}": f"F-{i}" for i in range(1, 8)}

# ---------------------------------------------------------------------------
# Round 3 -> Round 4 crosswalk.
# R4 id -> list of Round 3 statement ids (as keyed in statement_analyses.json).
# Two Round 3 pairs were merged into a single Round 4 statement (A-2+A-3 -> A02;
# C-6+C-11 -> C06). For merged entries the comparison pools the Round 3
# rating distributions of both source statements.
# ---------------------------------------------------------------------------
R4_TO_R3 = {
    "A01": ["A-1"],
    "A02": ["A-2", "A-3"],
    "A03": ["A-4"],
    "A04": ["A-5"],
    "A05": ["A-6"],
    "A06": ["A-7"],
    "A07": ["A-8"],
    "A08": ["A-9"],
    "A09": ["A-10"],
    "A10": ["A-11"],
    "A11": ["A-12"],
    "A12": ["A-13"],
    "A13": ["A-14"],
    "B01": ["B-1"], "B02": ["B-2"], "B03": ["B-3"], "B04": ["B-4"],
    "B05": ["B-5"], "B06": ["B-6"], "B07": ["B-7"], "B08": ["B-8"],
    "C01": ["C-1"], "C02": ["C-2"], "C03": ["C-3"], "C04": ["C-4"],
    "C05": ["C-5"], "C06": ["C-6", "C-11"], "C07": ["C-7"], "C08": ["C-8"],
    "C09": ["C-9"], "C10": ["C-10"],
    "D01": ["D-1"], "D02": ["D-2"], "D03": ["D-3"], "D04": ["D-4"], "D05": ["D-5"],
    "D06": ["D-6"], "D07": ["D-7"], "D08": ["D-8"], "D09": ["D-9"],
}


def ordered_ids():
    """Return R4 statement ids in canonical section/number order."""
    return list(R4_STATEMENTS.keys())


if __name__ == "__main__":
    # Quick self-check / crosswalk printout for sign-off.
    print(f"R4 statements: {len(R4_STATEMENTS)} "
          f"(A={sum(1 for s in R4_STATEMENTS.values() if s['section']=='A')}, "
          f"B={sum(1 for s in R4_STATEMENTS.values() if s['section']=='B')}, "
          f"C={sum(1 for s in R4_STATEMENTS.values() if s['section']=='C')}, "
          f"D={sum(1 for s in R4_STATEMENTS.values() if s['section']=='D')})")
    print(f"Crosswalk entries: {len(R4_TO_R3)}; "
          f"merged: {[k for k, v in R4_TO_R3.items() if len(v) > 1]}")
    print("\nR4 id  <-  Round 3 id(s)")
    for r4_id in ordered_ids():
        print(f"  {r4_id}  <-  {', '.join(R4_TO_R3[r4_id])}")

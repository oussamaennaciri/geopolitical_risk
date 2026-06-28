# Geopolitical Risk Scoring and Anomaly Detection

A data science practicum project at Regis University (MSDS692). It builds one system to measure and track geopolitical risk for every country, with two parts:

- A risk scorer that learns the Geopolitical Risk index from a country's structural features and scores every country, including the ones with no published index.
- An early warning detector that watches monthly news signals and flags a country that is moving away from its own normal.

## Results

- The scorer ranks unseen countries at a Spearman correlation of 0.81, and forecasts the next year at 0.91 with a mean absolute error of 0.11.
- It extends a risk score to all 247 countries, including the 203 the official index never covered.
- The detector catches 43 of 50 known crisis onsets, beats chance with a p value below 0.001, and fires about three months before the Russia and Ukraine invasion.

## Data

Nine open sources, joined into one country-year table of 2,470 country-years across 247 countries, 2015 to 2024. The GPR index is the target, the other eight are features: GDELT, World Bank WDI, V-Dem, UN Comtrade, the Global Sanctions Data Base, SIPRI, UNHCR, and UN General Assembly voting. Each source is cleaned on its own, then joined on a common country-year spine. The detector also uses the monthly GDELT table directly.

## Method

- Scorer: XGBoost, compared against a Random Forest, a linear ElasticNet, and a predict-the-mean baseline. Validated two ways, across unseen countries (GroupKFold) and forward in time (expanding window).
- Detector: a rolling z-score against each country's own 12-month baseline, compared against an Isolation Forest and a Local Outlier Factor. Validated against 50 known crisis onsets and a permutation test.

## Repository layout

```
.
├── data/                  # NOT in git (3+ GB), organized on disk only
│   ├── raw/               #   immutable source pulls, one folder per source
│   ├── interim/           #   per-source cleaned tables (one *_clean.csv each)
│   ├── processed/         #   model-ready joins and scores (master_v1, risk/anomaly scores)
│   ├── external/          #   reference lookups and geodata
│   └── _manifest.md       #   data provenance notes
├── notebooks/             # flat, filename prefix = pipeline stage (sorts in run order)
│   ├── acquire_*          #   data pulls (Comtrade)
│   ├── clean_*            #   one cleaner per source, writes to data/interim/<source>
│   ├── master_join        #   joins all clean sources into data/processed/master_v1
│   └── model_*            #   model_v1_risk (scorer), model_v2_anomaly (detector)
├── src/                   # Comtrade API pull scripts
├── reports/
│   ├── notes/             # model codebook and technical doc
│   ├── proposal/          # LaTeX report (IEEE template) and its figures/
│   └── Presentation.pptx
└── references/            # literature PDFs and citation notes, grouped by source
```

## Paths are location-independent

Every notebook starts with a small cell that locates the project root through the `.projectroot` marker file, then builds paths from it:

```python
from pathlib import Path
ROOT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / ".projectroot").exists())
df = pd.read_csv(ROOT / "data/interim/gpr/gpr_monthly.csv")
```

This means notebooks and scripts run correctly no matter where they live or which working directory they are launched from. Do not delete `.projectroot`.

## Reproduce

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

Run order follows the filename prefixes: `acquire_*`, then `clean_*` (run GPR first, the others cross-check against it), then `master_join`, then `model_*`. Listing `notebooks/` alphabetically already shows them in run order. Raw data is not versioned, so the cleaning notebooks expect the source files under `data/raw/<source>/`. See `data/_manifest.md`.

## Data note

The `data/` tree is excluded from version control through `.gitignore`, since it holds several multi-GB files. It is organized on disk but never committed.

## Use of AI tools

Anthropic's LLM "Claude" was used for coding help and polishing notebooks. All analysis, interpretation, and writing decisions are my own, and all text is in my own words.

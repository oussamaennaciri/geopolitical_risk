"""
Comtrade re-pull, paginated by year to dodge the 100K-record free-tier cap.
Per-year safety net: if a year returns >= 99,000 rows, re-pull that year split by flow.
Saves consolidated CSV to training_data/raw/comtrade/comtrade.csv.
"""
import os
import sys
import time
from pathlib import Path
import pandas as pd
import comtradeapicall as ct
from dotenv import load_dotenv

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".projectroot").exists())
load_dotenv(ROOT / ".env")
KEY = os.environ["COMTRADE_API_KEY"]
YEARS = list(range(2015, 2026))  # 2015..2025 inclusive
OUT_DIR = str(ROOT / "data/raw/comtrade")
os.makedirs(OUT_DIR, exist_ok=True)

CAP = 100_000
SAFETY = 99_000  # if a single call returns >= this, we suspect truncation


def pull_one(year, flow=None):
    """One API call. flow=None means both X and M; else 'X' or 'M'.
    Filters to TOTAL aggregates only on three dimensions:
      motCode=0       (all transport modes summed)
      customsCode=C00 (default customs procedure)
      partner2Code=0  (direct trade, no secondary partner breakdown)
    Without these the API returns every breakdown and explodes past 100K rows.
    """
    flow_arg = flow if flow else "X,M"
    print(f"  >>> year={year} flow={flow_arg} ...", end="", flush=True)
    t0 = time.time()
    df = ct.getFinalData(
        subscription_key=KEY,
        typeCode="C",
        freqCode="A",
        clCode="HS",
        period=str(year),
        reporterCode=None,
        cmdCode="TOTAL",
        flowCode=flow_arg,
        partnerCode=None,
        partner2Code="0",
        customsCode="C00",
        motCode="0",
        format_output="JSON",
    )
    dt = time.time() - t0
    print(f" {len(df):,} rows in {dt:.1f}s")
    return df


def pull_year_safe(year):
    """Pull one year. If suspicious of truncation, fall back to per-flow."""
    df = pull_one(year)
    if len(df) >= SAFETY:
        print(f"    !! year {year} returned {len(df):,} rows (>= {SAFETY:,}) -- likely truncated. Splitting by flow.")
        df_x = pull_one(year, flow="X")
        df_m = pull_one(year, flow="M")
        df = pd.concat([df_x, df_m], ignore_index=True)
        if len(df_x) >= SAFETY or len(df_m) >= SAFETY:
            print(f"    !! still suspicious after split (X={len(df_x):,}, M={len(df_m):,}). Manual review needed.")
    return df


def main():
    print(f"Comtrade pull: {YEARS[0]}..{YEARS[-1]} ({len(YEARS)} years)")
    all_frames = []
    for y in YEARS:
        df = pull_year_safe(y)
        df["__pulled_year_param__"] = y
        all_frames.append(df)
    out = pd.concat(all_frames, ignore_index=True)
    out = out.drop(columns="__pulled_year_param__")

    out_path = os.path.join(OUT_DIR, "comtrade.csv")
    out.to_csv(out_path, index=False)

    print()
    print("=" * 70)
    print(f"DONE. Consolidated: {len(out):,} rows x {out.shape[1]} cols")
    print(f"Saved to: {out_path}")
    print()
    print("Rows per period (should cover all 11 years):")
    print(out["period"].value_counts().sort_index().to_string())
    print()
    print("Distinct reporters per period:")
    rc = out.groupby("period")["reporterCode"].nunique()
    print(rc.to_string())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

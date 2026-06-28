"""
Comtrade strategic-commodity pull WITH mode of transport.
8 HS2 chapters, yearly 2015-2025, motCode=None.
motCode=None returns the TOTAL (motCode=0, 100% coverage) PLUS the per-mode
breakdown where reporters provide it (~42% coverage). So one pull gives both
the complete totals and the partial mode detail (pipeline, sea, rail, road, air).
One call per chapter-year; if a chapter-year nears the 100K cap, split by flow.
Saves to training_data/raw/comtrade/comtrade_commodities.csv.
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
YEARS = list(range(2015, 2026))
CHAPTERS = {
    "27": "Energy (oil, gas, coal)",
    "85": "Electronics",
    "30": "Pharmaceuticals",
    "71": "Gold & precious metals",
    "26": "Ores / critical minerals",
    "10": "Cereals",
    "31": "Fertilizers",
    "93": "Arms & ammunition",
}
OUT_DIR = str(ROOT / "data/raw/comtrade")
os.makedirs(OUT_DIR, exist_ok=True)
SAFETY = 99_000


def pull(year, cmd, flow="X,M"):
    return ct.getFinalData(
        subscription_key=KEY, typeCode="C", freqCode="A", clCode="HS",
        period=str(year), reporterCode=None, cmdCode=cmd, flowCode=flow,
        partnerCode=None, partner2Code="0", customsCode="C00", motCode=None,
        format_output="JSON",
    )


def pull_safe(year, cmd):
    df = pull(year, cmd)
    if len(df) >= SAFETY:
        dx = pull(year, cmd, "X")
        dm = pull(year, cmd, "M")
        df = pd.concat([dx, dm], ignore_index=True)
        print("      (split by flow to dodge cap)")
    return df


def main():
    n = len(CHAPTERS) * len(YEARS)
    print(f"Commodity + mode pull: {len(CHAPTERS)} chapters x {len(YEARS)} years = {n} base calls")
    frames = []
    i = 0
    for ch, label in CHAPTERS.items():
        for y in YEARS:
            i += 1
            t0 = time.time()
            df = pull_safe(y, ch)
            dt = time.time() - t0
            modes = df[df["motCode"] != 0]["reporterCode"].nunique() if "motCode" in df.columns else 0
            print(f"  [{i:>2}/{n}] HS{ch} {label[:20]:20s} {y}  {len(df):>6,} rows  "
                  f"{modes:>3} reporters w/mode  {dt:4.0f}s", flush=True)
            frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out_path = os.path.join(OUT_DIR, "comtrade_commodities.csv")
    out.to_csv(out_path, index=False)

    print("\n" + "=" * 64)
    print(f"DONE. {len(out):,} rows x {out.shape[1]} cols -> {out_path}")
    print("\nRows per chapter:")
    print(out["cmdCode"].astype(str).value_counts().to_string())
    print("\nMode coverage (rows per motCode):")
    print(out["motCode"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

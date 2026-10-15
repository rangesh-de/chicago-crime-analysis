"""
Download Chicago crime records from the City of Chicago open data API (Socrata).

Only the columns the analysis needs are requested, and the data comes down in
pages of 50,000 rows. The result is saved as Parquet, which is much smaller and
faster to load than CSV.

Usage:
    python scripts/download_data.py                      # 2019-2025 (about 1.7M rows)
    python scripts/download_data.py --start 2023 --end 2025

Optional: set SOCRATA_APP_TOKEN (free, from data.cityofchicago.org) for faster,
less throttled downloads. It works without one.
"""
import argparse
import os
import time
from pathlib import Path

import pandas as pd
import requests

URL = "https://data.cityofchicago.org/resource/ijzp-q8t2.json"
COLUMNS = [
    "id", "case_number", "date", "primary_type", "description", "location_description",
    "arrest", "domestic", "district", "community_area", "year", "latitude", "longitude",
]
PAGE_SIZE = 50_000
OUT_DIR = Path(__file__).resolve().parent.parent / "data"


def fetch_page(session, start, end, offset):
    params = {
        "$select": ",".join(COLUMNS),
        "$where": f"year between {start} and {end}",
        "$order": "id",                # stable order so paging never skips or repeats rows
        "$limit": PAGE_SIZE,
        "$offset": offset,
    }
    for attempt in range(5):
        try:
            resp = session.get(URL, params=params, timeout=120)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as err:
            wait = 2 ** attempt * 5
            print(f"  request failed ({err}); retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError("Giving up after 5 failed attempts")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=2019)
    parser.add_argument("--end", type=int, default=2025)
    args = parser.parse_args()

    session = requests.Session()
    token = os.getenv("SOCRATA_APP_TOKEN")
    if token:
        session.headers["X-App-Token"] = token

    pages, offset = [], 0
    print(f"Downloading {args.start}-{args.end}")
    while True:
        rows = fetch_page(session, args.start, args.end, offset)
        if not rows:
            break
        pages.append(pd.DataFrame(rows))
        offset += len(rows)
        print(f"  {offset:>10,} rows")
        if len(rows) < PAGE_SIZE:
            break

    df = pd.concat(pages, ignore_index=True)
    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / f"crimes_{args.start}_{args.end}.parquet"
    df.to_parquet(out, index=False)
    print(f"Saved {len(df):,} rows to {out}")


if __name__ == "__main__":
    main()

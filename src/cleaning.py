"""
Cleaning and feature engineering for Chicago crime data.

Kept in a module (not inside the notebook) so the logic is reusable and testable.
"""
import pandas as pd

from src.community_areas import COMMUNITY_AREAS

# Chicago's rough bounding box. A few records are geocoded far outside the city.
LAT_RANGE = (41.6, 42.1)
LON_RANGE = (-88.0, -87.5)

SEASONS = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring", 5: "Spring",
           6: "Summer", 7: "Summer", 8: "Summer", 9: "Fall", 10: "Fall", 11: "Fall"}


def quality_report(df: pd.DataFrame) -> pd.DataFrame:
    """Null counts and share per column, to look at before cleaning."""
    nulls = df.isna().sum()
    return pd.DataFrame({"nulls": nulls, "null_pct": (100 * nulls / len(df)).round(2)}).sort_values(
        "nulls", ascending=False
    )


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Return a cleaned copy plus a log of what was changed, so every step is accounted for."""
    df = raw.copy()
    log = {"rows_in": len(df)}

    before = len(df)
    df = df.drop_duplicates(subset="id")
    log["duplicate_ids_dropped"] = before - len(df)

    # Types: the API returns everything as text
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["arrest", "domestic"]:
        df[col] = df[col].astype(str).str.lower().eq("true")
    for col in ["latitude", "longitude"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["community_area"] = pd.to_numeric(df["community_area"], errors="coerce").astype("Int64")
    df["district"] = pd.to_numeric(df["district"], errors="coerce").astype("Int64")

    before = len(df)
    df = df.dropna(subset=["date", "primary_type"])
    log["missing_date_or_type_dropped"] = before - len(df)

    # Bad coordinates become missing (the incident still counts, it just can't be mapped)
    bad_geo = ~(df["latitude"].between(*LAT_RANGE) & df["longitude"].between(*LON_RANGE))
    log["coordinates_set_missing"] = int((bad_geo & df["latitude"].notna()).sum())
    df.loc[bad_geo, ["latitude", "longitude"]] = pd.NA

    # Community area 0 is not a real area
    log["invalid_community_area"] = int((df["community_area"] == 0).sum())
    df.loc[df["community_area"] == 0, "community_area"] = pd.NA
    df["community_name"] = df["community_area"].map(COMMUNITY_AREAS)

    # Text tidy-up: the source mixes cases and spellings
    df["primary_type"] = df["primary_type"].str.strip().str.upper()
    df["primary_type"] = df["primary_type"].replace({"NON - CRIMINAL": "NON-CRIMINAL",
                                                     "NON-CRIMINAL (SUBJECT SPECIFIED)": "NON-CRIMINAL"})
    df["location_description"] = df["location_description"].fillna("UNKNOWN").str.strip().str.upper()

    # Features for the analysis
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df["hour"] = df["date"].dt.hour
    df["weekday"] = df["date"].dt.day_name()
    df["is_weekend"] = df["date"].dt.dayofweek >= 5
    df["season"] = df["date"].dt.month.map(SEASONS)
    # Many records are logged at exactly midnight because the true time is unknown
    df["time_is_midnight"] = (df["date"].dt.hour == 0) & (df["date"].dt.minute == 0)

    log["rows_out"] = len(df)
    return df.reset_index(drop=True), log

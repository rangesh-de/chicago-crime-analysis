import pandas as pd

from src.cleaning import clean


def raw_rows():
    return pd.DataFrame({
        "id": ["1", "2", "2", "3", "4"],
        "case_number": ["A", "B", "B", "C", "D"],
        "date": ["2024-07-04T21:15:00.000", "2024-01-02T00:00:00.000", "2024-01-02T00:00:00.000",
                 "not a date", "2023-12-25T08:30:00.000"],
        "primary_type": ["THEFT", "battery ", "battery ", "THEFT", "NON - CRIMINAL"],
        "description": ["x"] * 5,
        "location_description": ["STREET", None, None, "STREET", "residence"],
        "arrest": [True, False, False, False, "true"],
        "domestic": [False, True, True, False, False],
        "district": ["1", "2", "2", "3", "4"],
        "community_area": ["32", "0", "0", "8", "77"],
        "year": ["2024", "2024", "2024", "2024", "2023"],
        "latitude": ["41.88", "36.61", "36.61", "41.9", None],
        "longitude": ["-87.63", "-91.68", "-91.68", "-87.6", None],
    })


def test_duplicates_and_bad_dates_are_dropped_and_logged():
    df, log = clean(raw_rows())
    assert log["duplicate_ids_dropped"] == 1
    assert log["missing_date_or_type_dropped"] == 1
    assert log["rows_out"] == 3 == len(df)


def test_types_are_converted():
    df, _ = clean(raw_rows())
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert df["arrest"].tolist() == [True, False, True]
    assert df["domestic"].dtype == bool


def test_out_of_city_coordinates_become_missing():
    df, log = clean(raw_rows())
    assert log["coordinates_set_missing"] == 1
    assert df.loc[df["id"] == "2", "latitude"].isna().all()
    assert df.loc[df["id"] == "1", "latitude"].iloc[0] == 41.88


def test_community_area_zero_is_missing_and_names_are_mapped():
    df, _ = clean(raw_rows())
    names = dict(zip(df["id"], df["community_name"]))
    assert names["1"] == "Loop"
    assert pd.isna(names["2"])
    assert names["4"] == "Edgewater"


def test_text_is_standardized_and_features_added():
    df, _ = clean(raw_rows())
    row = df.set_index("id")
    assert row.loc["2", "primary_type"] == "BATTERY"
    assert row.loc["4", "primary_type"] == "NON-CRIMINAL"
    assert row.loc["2", "location_description"] == "UNKNOWN"
    assert bool(row.loc["2", "time_is_midnight"]) is True
    assert row.loc["1", "hour"] == 21
    assert row.loc["1", "season"] == "Summer"
    assert row.loc["4", "weekday"] == "Monday"

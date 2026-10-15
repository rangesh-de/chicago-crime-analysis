# Walkthrough

How the project works, piece by piece, and what to say about each part in an interview.

## The download script

- The city API (Socrata) returns at most a fixed number of rows per request, so the script asks for pages of 50,000 using `$limit` and `$offset`.
- `$order=id` matters: without a fixed order, the API can return rows in a different order on each page, so pages could overlap or skip rows.
- `$select` asks only for the 13 columns the analysis uses, which makes the download much smaller.
- Failed requests retry with exponential backoff (5s, 10s, 20s ...). Long downloads from public APIs fail occasionally, and a script should survive that.
- Saved as **Parquet**, not CSV: about 5–10x smaller, keeps data types, and loads much faster.
- **Interview line:** "I wrote the extraction to be repeatable: paging with a stable sort, retries, and only the columns I need."

## Cleaning (`src/cleaning.py`)

- The API returns everything as text, so dates, booleans and numbers are converted explicitly.
- `clean()` returns the cleaned data **and a log** of how many rows each step touched. That's an audit trail: you can say exactly what you changed and why.
- Cleaning lives in a module instead of the notebook so it can be **unit tested** (`tests/test_cleaning.py`). Tests use a few hand-made rows where the right answer is known.
- **Interview line:** "I kept cleaning logic out of the notebook so it was testable and reusable."

## The analysis decisions worth explaining

**Check the midnight problem before the hourly analysis.** Incidents with an unknown time are recorded at 00:00. Without checking, you'd report "crime peaks at midnight," which is a data artifact. This is the strongest example in the project of checking data before trusting it.

**Index to 2019 = 100.** Theft and narcotics have very different volumes, so plotting raw counts on one chart hides the smaller type's changes. Indexing puts every type on the same scale, so the chart shows relative change.

**Arrest rate is about how a crime is discovered.** Narcotics and weapons violations are mostly found *by* police, so arrest rates are high. Theft is reported later by victims, so rates are low. Saying this shows you interpret numbers instead of just reporting them.

**Raw counts vs per-capita.** Busy areas like the Loop have many visitors. Admitting the limitation, and naming the fix (census population data), is better than overclaiming.

**Pareto check on areas.** "Half of all incidents occur in N of 77 areas" turns a bar chart into a statement about where resources would have the most effect.

## Questions an interviewer might ask

- *Why pandas and not SQL?* Both work. Pandas fit because the analysis is exploratory and visual. For a production dashboard, the aggregations would move to SQL.
- *How would you scale this to all 8M rows since 2001?* Read only needed columns from Parquet, use categorical dtypes for text columns, or switch to DuckDB or Polars, which handle this size easily on a laptop.
- *What would you do next?* Per-capita rates with census data, joining weather data to test the "hot days, more crime" idea, and forecasting monthly incidents.

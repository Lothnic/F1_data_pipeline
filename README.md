# F1 Data Pipeline

An early-stage Formula 1 data project using [FastF1](https://docs.fastf1.dev/). It contains a local fastest-lap plot and a session extractor that writes Parquet files to Google Cloud Storage (GCS).

## Project status

This is a prototype, not a complete automated pipeline. The raw ingestion DAG is a placeholder and does not schedule extraction. The hello-world DAG is only an Airflow connectivity example. Files in `tempfiles/` are historical experiments and are not supported. There is no transformation layer, dashboard, deployment configuration, or production monitoring yet.

## Getting started

Requirements: Python 3.10 or later, [uv](https://docs.astral.sh/uv/getting-started/installation/), and internet access. From the repository root:

```bash
uv sync --locked
uv run main.py --year 2024 --drivers VER PIA NOR --output fastest-laps.png
```

Add `--round 1` to process a single round. Omit `--output` to display the chart in a desktop window. The script loads race sessions for the season and plots each driver's fastest lap time against its lap number; it skips sessions it cannot load. The first run can take time and download substantial data. FastF1's cache is created in `f1_cache/` automatically. The chart is exploratory: times across different circuits are not directly comparable.

## Test extraction locally

Write available session data to local Parquet files without GCS credentials:

```bash
uv run python -m scripts.fastf1_extractor 2024 1 R --output-dir ./data
```

The command reports which datasets were saved. FastF1 can return only partial data when an upstream source is unavailable, so check that the datasets you need were produced. The `data/` directory can grow large and is ignored by Git.

## Extract a session to GCS

Create a GCS bucket and configure [Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc) for an identity with permission to write objects. Set the project and bucket names in your shell, then run:

```bash
export GCP_PROJECT_ID="your-project-id"
export GCS_BUCKET_NAME="your-bucket-name"
uv run python -m scripts.fastf1_extractor 2024 1 R
```

The positional arguments are year, championship round, and FastF1 session identifier (for example `R` for race or `Q` for qualifying). The extractor loads laps, results and weather when available, skips empty or unavailable datasets, and fails if none are available. Objects are written to:

```text
raw/fastf1/year=2024/round=1/session_type=R/{laps,results,weather_data}.parquet
```

Only available, nonempty datasets are written. Timedeltas are stored as seconds, with missing values retained as nulls. Re-running the same session overwrites objects that are uploaded; it does not delete older objects for datasets that are now empty. A failed run may leave a partial set of objects. Set `FASTF1_CACHE_DIR` to change the extractor's cache location. Cloud usage and API access may incur costs.

The extractor function can be called from an Airflow task, but deploying and scheduling it in Airflow/Cloud Composer, including making the module and dependencies available to workers, is still work to be done. The local dependencies do not install Airflow.

## Tests

```bash
uv run python -m pytest
```

The tests use mocked FastF1 and GCS clients; they do not verify access to real sessions or cloud resources. Use the local extraction command above for a live smoke test.

## Files

- `main.py`: local plotting script.
- `scripts/fastf1_extractor.py`: session extraction and GCS upload.
- `dags/`: a placeholder for ingestion and an Airflow hello-world example.
- `test/`: offline extractor tests.
- `dailylog.md` and `tempfiles/`: historical notes and experiments.

FastF1 is an independent project; consult its documentation for data availability and usage conditions. No license has been specified for this repository; obtain permission from the owner before redistributing or reusing it.

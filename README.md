# F1 Data Pipeline & Race Outcome Analysis

A reproducible data science project exploring how starting position, driver and constructor relate to Formula 1 race classification. Includes source caching, validation, descriptive analysis, a chronological prediction experiment, Parquet storage and an optional GCS/Airflow ingestion path.

## Run the analysis

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and use Python 3.10 or later:

```bash
uv sync --locked
uv run python -m f1_pipeline.analysis --year 2024
uv run python -m pytest
```

The first analysis run requires internet access. Source JSON is cached in `data/source/`. Subsequent runs can use that cache. Delete the season's cached files to refresh. Outputs in `data/analysis/`:

- `analysis.png`: top drivers by race points and holdout prediction plot.
- `results.parquet`: validated race results.
- `driver_summary.csv`: race points and average classified position.
- `holdout_predictions.csv`: individual model and baseline predictions.
- `metrics.json`: train/test rounds, row counts and errors.

To analyze a previously exported results CSV:

```bash
uv run python -m f1_pipeline.analysis --input results.csv --output data/custom
```

CSV columns: `round,race,driver,constructor,grid,position,points,status`. Use numeric rounds, grid, position and points. The validator rejects missing data, duplicate driver-round entries and invalid numeric values. Use one season per input; combining seasons would create duplicate round identities.

## Verified experiment

A live 2024 run returned 479 race entries. The first 18 rounds (359 entries) were used for training; the final six rounds (120 entries) were held out:

| Method | Holdout MAE, finishing positions |
| --- | ---: |
| Predict starting grid | 3.60 |
| Ridge regression | 3.13 |

Lower is better. This is one season and one holdout, not evidence of performance across seasons. No hyperparameter search was conducted. Read [methodology](docs/METHODOLOGY.md) for assumptions, limitations and interview discussion points.

## FastF1 session extraction

For detailed laps/results/weather, write available datasets locally:

```bash
uv run python -m scripts.fastf1_extractor 2024 1 R --output-dir data/raw
```

For GCS, configure [Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc) with object-write permission, then:

```bash
export GCP_PROJECT_ID="your-project-id"
export GCS_BUCKET_NAME="your-bucket-name"
uv run python -m scripts.fastf1_extractor 2024 1 R
```

Files use `raw/fastf1/year=2024/round=1/session_type=R/` partitions. Timedeltas become seconds and missing values remain null. Empty or unavailable datasets are skipped and saved datasets are reported. Runs fail if none are available. Re-runs overwrite individual files; writes are not atomic across datasets and older files are not deleted. A partial extraction is not a complete session.

Live timing requests returned HTTP 401 in the development environment. Results were still available through the fallback service. The analysis command above uses the working Jolpica results API directly, without requiring lap timing. Authentication restrictions cannot be repaired by changing local parsing code.

## Optional fastest-lap plot

```bash
uv run main.py --year 2024 --round 1 --drivers VER PIA NOR --output fastest-laps.png
```

Requires working FastF1 lap access. Omit `--round` for a season, or `--output` for a desktop window. The chart shows fastest lap time against lap number; times from different circuits are not directly comparable.

## Airflow deployment

`dags/f1_raw_ingestion_dag.py` defines an Airflow 2.x DAG with manual year/round/session parameters, two retries and one active run. Deploy the DAG to a separately provisioned Airflow environment; install the runtime dependencies and make the repository root importable on every worker. Configure GCS credentials and environment variables there. Trigger `f1_raw_ingestion` manually. Airflow is not installed in the local analysis environment; this DAG has not been integration-tested on Composer. The hello-world DAG is a separate connectivity example.

## Layout and verification

`f1_pipeline/` contains the analysis; `scripts/` handles raw extraction; `test/` has offline tests for serialization, missing datasets, quality rules, chronological splitting and exclusion of post-race points from model features. GitHub Actions runs the tests on pushes and pull requests. Historical experiments in `tempfiles/` and `dailylog.md` are not part of the supported workflow.

Data comes from [Jolpica](https://github.com/jolpica/jolpica-f1) and [FastF1](https://docs.fastf1.dev/). Follow their access and usage terms. No license has been selected for this repository; contact its owner before reusing or redistributing the code.

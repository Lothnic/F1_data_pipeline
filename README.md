# F1 Data Pipeline & Race Outcome Analysis

[![Tests](https://github.com/Lothnic/F1_data_pipeline/actions/workflows/tests.yml/badge.svg)](https://github.com/Lothnic/F1_data_pipeline/actions/workflows/tests.yml)

Analyze Formula 1 race results from **1950 through the latest available season**, with reproducible data ingestion, validation, driver summaries and a chronological machine-learning experiment.

The project asks: **Can starting position, driver and constructor predict finishing position better than starting position alone?** It provides a complete local analysis workflow, plus optional FastF1 extraction to Parquet or Google Cloud Storage.

**Latest verified snapshot — November 3, 2026:** 77 seasons, 1,168 races and 26,291 result entries, through the 2026 Mexico City Grand Prix (round 19, November 1). This is a dated snapshot; the default command discovers the latest season from the data provider on each run.

## Run the analysis

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and use Python 3.10 or later:

```bash
git clone https://github.com/Lothnic/F1_data_pipeline.git
cd F1_data_pipeline
uv sync --locked
uv run python -m f1_pipeline.analysis
uv run python -m pytest
```

By default the analysis fetches every season from 1950 through the latest season reported by Jolpica. Only published race results are included; future races are excluded. Use `--year 2024` for one season or `--start-year 2018 --end-year 2026` for a range. The latest selected season is refreshed on every API run; use `--refresh` to refresh the bulk archive or historical API pages too.

The first full-history run requires internet access. It downloads Jolpica’s public delayed bulk CSV archive, normalizes the relational tables, and replaces the latest selected season with fresh API results. The archive and source JSON are cached in `data/source/`. Use `--source api` for the slower paginated-only path. Subsequent runs reuse historical data, but still require network access to discover and refresh the latest selected season. A fresh bulk download is checked against the provider's SHA-256 hash.

### Common commands

```bash
# One season
uv run python -m f1_pipeline.analysis --year 2024

# A range ending at the latest available season
uv run python -m f1_pipeline.analysis --start-year 2018

# A fixed range
uv run python -m f1_pipeline.analysis --start-year 2018 --end-year 2026

# Refresh historical source data as well
uv run python -m f1_pipeline.analysis --refresh

# Use paginated API results for every selected season
uv run python -m f1_pipeline.analysis --source api --start-year 2024
```

API requests use throttling, bounded concurrency and retries. A paginated full-history download can encounter provider rate limits; completed pages remain cached for a subsequent run. The bulk path is the default to reduce request volume.

### Generated outputs

Outputs are written to `data/analysis/`:

- `analysis.png`: top drivers by race points and holdout prediction plot.
- `results.parquet`: validated race results.
- `driver_summary.csv`: race points and average classified position per season and driver.
- `season_coverage.csv`: race and entry counts for each season.
- `manifest.json`: run time, coverage and latest included round.
- `holdout_predictions.csv`: individual model and baseline predictions.
- `metrics.json`: train/test season-round keys, row counts and errors.

To analyze a previously exported results CSV:

```bash
uv run python -m f1_pipeline.analysis --input results.csv --output data/custom
```

CSV columns: `season,round,race,driver,constructor,grid,position,points,status`. Use numeric season, round, grid, position and points. With `--input`, analysis runs without fetching source data. The validator rejects missing data, duplicate season-round-driver-position entries and invalid numeric values. Season and round together identify a race. Historic shared drives can give one driver more than one classified entry; these entries are preserved, with position included in the uniqueness key.

## Verified full-history run

The verified 1950–2026 run uses the earliest 75% of race events for training and the remaining events for evaluation. All entries from a race stay in the same split.

| Method | Full-history holdout MAE (positions) |
| --- | ---: |
| Predict starting-grid position | **3.77** |
| Ridge regression | 4.07 |

Lower is better. **The baseline outperforms the model on this historical split.** Fitting fixed driver and team effects across decades does not capture changes in car performance, regulations or reliability. This is an observed limitation of the current model, not a claim that more historical data improves prediction.

Only grid position, driver and constructor are predictors. Encoding and scaling are fitted on training data; points, status and finishing position are excluded from predictors. Future events and bulk-archive entries without a recorded finishing position are excluded. Retirements with recorded positions remain included.

![Latest-season points and full-history holdout](reports/analysis.png)

Inspect the committed [coverage report](reports/season_coverage.csv), [run manifest](reports/manifest.json), [evaluation metrics](reports/metrics.json) and [archive metadata](reports/source-archive.json). These files describe the verified snapshot; running the analysis writes new outputs under `data/analysis/` without updating committed reports automatically.

## Reference single-season experiment

A live 2024 run returned 479 race entries. The first 18 rounds (359 entries) were used for training; the final six rounds (120 entries) were held out:

| Method | Holdout MAE, finishing positions |
| --- | ---: |
| Predict starting grid | 3.60 |
| Ridge regression | 3.13 |

The full-history command evaluates on the last quarter of season-round event keys and reports its own metrics. The chart shows points for the latest included season; cumulative points across eras are not comparable because scoring systems changed.

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

Live timing requests returned HTTP 401 in the development environment. Results were still available through the fallback service. The main analysis uses Jolpica’s bulk archive and results API, so it does not depend on FastF1 lap-timing access. The full-history workflow covers race results; it does not promise historical telemetry or weather for every race.

## Optional fastest-lap plot

```bash
uv run main.py --year 2024 --round 1 --drivers VER PIA NOR --output fastest-laps.png
```

Requires working FastF1 lap access. Omit `--round` for a season, or `--output` for a desktop window. The chart shows fastest lap time against lap number; times from different circuits are not directly comparable.

## Airflow deployment

`dags/f1_raw_ingestion_dag.py` defines an Airflow 2.x DAG with manual year/round/session parameters, two retries and one active run. Deploy the DAG to a separately provisioned Airflow environment; install the runtime dependencies and make the repository root importable on every worker. Configure GCS credentials and environment variables there. Trigger `f1_raw_ingestion` manually. Airflow is not installed in the local analysis environment; this DAG has not been integration-tested on Composer. The hello-world DAG is a separate connectivity example.

## Project layout and verification

```text
f1_pipeline/analysis.py       CLI, validation, evaluation and chart generation
f1_pipeline/history.py        Bulk archive normalization and latest-season refresh
scripts/fastf1_extractor.py   Local/GCS session extraction
dags/                        Manual ingestion and connectivity examples
test/                        Offline regression and data-quality tests
reports/                     Committed results from the verified run
docs/METHODOLOGY.md           Assumptions, limitations and interview discussion
.github/workflows/tests.yml  Automated test workflow
```

The verified suite contains **15 passing tests**, covering archive joins, race-session filtering, latest-season replacement, cache parsing, multi-season identities, shared drives, chronological splitting, leakage prevention and Parquet serialization. Run `uv run python -m pytest` locally. GitHub Actions runs the same suite on pushes and pull requests. Offline tests do not establish live API or cloud availability.

Historical experiments in `tempfiles/` and `dailylog.md` are outside the supported workflow.

## Next experiments

- Compare rolling recent-season training windows with the same grid baseline.
- Hold out an untouched season and report race-level error variation.
- Add retirement modeling and enforce a valid predicted finishing order.
- Add atomic dataset publication and integration-test the Airflow/GCS deployment.

## Data sources and license

Race results come from [Jolpica F1](https://github.com/jolpica/jolpica-f1); detailed session extraction uses [FastF1](https://docs.fastf1.dev/). Jolpica data is provided under CC BY-NC-SA 4.0 according to its [terms](https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md). Follow each provider's usage and access conditions.

The repository has no selected code license. Data-provider licenses do not grant a license to this project's code.

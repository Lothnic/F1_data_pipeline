"""Acquire, validate and evaluate race results without using post-race predictors."""
from __future__ import annotations

import argparse
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


_LOCAL = threading.local()
_REQUEST_LOCK = threading.Lock()
_LAST_REQUEST = 0.0


def _get(url, **kwargs):
    global _LAST_REQUEST
    if not hasattr(_LOCAL, "http"):
        _LOCAL.http = requests.Session()
        _LOCAL.http.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])))
    with _REQUEST_LOCK:
        time.sleep(max(0, .8 - (time.monotonic() - _LAST_REQUEST)))
        _LAST_REQUEST = time.monotonic()
    return _LOCAL.http.get(url, **kwargs)


def fetch_season(year: int, cache: Path, refresh: bool = False) -> pd.DataFrame:
    """Cache source responses; explicit refresh is achieved by removing the cache."""
    cache.mkdir(parents=True, exist_ok=True)
    races = []
    offset = 0
    while True:
        path = cache / f"{year}-results-{offset}.json"
        if path.exists() and not refresh:
            payload = json.loads(path.read_text())
        else:
            response = _get(
                f"https://api.jolpi.ca/ergast/f1/{year}/results/",
                params={"limit": 100, "offset": offset}, timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            path.write_text(json.dumps(payload, indent=2))
        data = payload["MRData"]
        races.extend(data["RaceTable"]["Races"])
        offset += int(data["limit"])
        if offset >= int(data["total"]):
            break
    rows = []
    for race in races:
        for result in race["Results"]:
            rows.append({"season": int(race["season"]), "round": int(race["round"]), "race": race["raceName"],
                         "driver": result["Driver"]["driverId"],
                         "constructor": result["Constructor"]["constructorId"],
                         "grid": int(result["grid"]), "position": int(result["position"]),
                         "points": float(result["points"]), "status": result["status"]})
    if len(rows) != int(data["total"]):
        raise ValueError(f"Incomplete pagination for {year}: expected {data['total']} entries, got {len(rows)}")
    return pd.DataFrame(rows, columns=["season", "round", "race", "driver", "constructor", "grid", "position", "points", "status"])


def available_seasons() -> list[int]:
    response = _get("https://api.jolpi.ca/ergast/f1/seasons/", params={"limit": 100}, timeout=30)
    response.raise_for_status()
    return sorted(int(row["season"]) for row in response.json()["MRData"]["SeasonTable"]["Seasons"])


def fetch_history_api(start: int, end: int, cache: Path, refresh: bool = False) -> pd.DataFrame:
    def load(year):
        frame = fetch_season(year, cache, refresh=refresh or year == end)
        print(f"{year}: {len(frame)} result entries", flush=True)
        return frame

    # Bounded workers hide network latency; request starts share a global throttle.
    with ThreadPoolExecutor(max_workers=3) as pool:
        frames = list(pool.map(load, range(start, end + 1)))
    return pd.concat(frames, ignore_index=True)


def fetch_history(start: int, end: int, cache: Path, refresh: bool = False):
    from .history import fetch_bulk_history
    return fetch_bulk_history(start, end, cache, refresh, _get, fetch_season)


def validate(frame: pd.DataFrame) -> None:
    required = {"season", "round", "race", "driver", "constructor", "grid", "position", "points", "status"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if frame.empty or frame[list(required)].isna().any().any():
        raise ValueError("Results must be nonempty and contain no missing required values")
    if frame.duplicated(["season", "round", "driver", "position"]).any():
        raise ValueError("Duplicate result entries within a season and round")
    for column in ("season", "round", "grid", "position", "points"):
        if not pd.api.types.is_numeric_dtype(frame[column]):
            raise ValueError(f"{column} must be numeric")
    if (frame["round"] < 1).any() or (frame["grid"] < 0).any() or (frame["position"] < 1).any() or (frame["points"] < 0).any():
        raise ValueError("Invalid negative or zero values in race results")


def evaluate(frame: pd.DataFrame):
    """Hold out the last quarter of rounds, never randomly split race entries."""
    validate(frame)
    events = sorted(set(zip(frame["season"], frame["round"])))
    if len(events) < 4:
        raise ValueError("At least four rounds are needed for a chronological holdout")
    cutoff = events[max(1, int(len(events) * .75))]
    keys = pd.Series(list(zip(frame["season"], frame["round"])), index=frame.index)
    train = frame[keys < cutoff].copy()
    test = frame[keys >= cutoff].copy()
    # Grid zero denotes no normal grid slot; map it to the end of the field.
    # The value is fitted only from training data.
    back = int(train["position"].max())
    for part in (train, test):
        part.loc[part["grid"] == 0, "grid"] = back
    features = ["grid", "driver", "constructor"]
    preprocessing = ColumnTransformer([
        ("grid", StandardScaler(), ["grid"]),
        ("identity", OneHotEncoder(handle_unknown="ignore"), ["driver", "constructor"]),
    ])
    model = make_pipeline(preprocessing, Ridge(alpha=10, solver="lsqr"))
    model.fit(train[features], train["position"])
    predictions = model.predict(test[features]).clip(1, back)
    output = test.copy()
    output["prediction"] = predictions
    output["grid_baseline"] = test["grid"]
    metrics = {"train_events": [list(map(int, e)) for e in events if e < cutoff],
               "test_events": [list(map(int, e)) for e in events if e >= cutoff],
               "train_rows": len(train), "test_rows": len(test),
               "ridge_mae": mean_absolute_error(test["position"], predictions),
               "grid_baseline_mae": mean_absolute_error(test["position"], test["grid"])}
    return metrics, output


def run(frame: pd.DataFrame, output: Path):
    metrics, predictions = evaluate(frame)
    output.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output / "results.parquet", index=False)
    predictions.to_csv(output / "holdout_predictions.csv", index=False)
    coverage = frame.groupby("season").agg(races=("round", "nunique"), entries=("driver", "size"))
    coverage.to_csv(output / "season_coverage.csv")
    (output / "manifest.json").write_text(json.dumps({"retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "first_season": int(frame.season.min()), "last_season": int(frame.season.max()), "races": int(coverage.races.sum()), "entries": len(frame), "latest_round": int(frame.loc[frame.season == frame.season.max(), "round"].max()), "source": "Jolpica bulk CSV archive plus refreshed latest-season API results; historical cache may predate this run"}, indent=2))
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2))
    summary = frame.groupby(["season", "driver"]).agg(points=("points", "sum"), mean_finish=("position", "mean"), races=("round", "nunique")).sort_values("points", ascending=False)
    summary.to_csv(output / "driver_summary.csv")
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    latest = summary.loc[int(frame.season.max())].sort_values("points", ascending=False)
    latest.head(10)["points"].sort_values().plot.barh(ax=axes[0], color="#2563eb")
    axes[0].set(title=f"{int(frame.season.max())} race points — top 10 drivers", xlabel="Points (sprints excluded)", ylabel="")
    axes[1].scatter(predictions["position"], predictions["prediction"], alpha=.4)
    axes[1].plot([1, frame.position.max()], [1, frame.position.max()], "k--", linewidth=1)
    axes[1].set(title="Later-race holdout predictions", xlabel="Actual classified position", ylabel="Predicted position")
    fig.tight_layout()
    fig.savefig(output / "analysis.png", dpi=160)
    plt.close(fig)
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, help="Process one season")
    parser.add_argument("--start-year", type=int, default=1950)
    parser.add_argument("--end-year", type=int, help="Default: latest season returned by the API")
    parser.add_argument("--source", choices=["bulk", "api"], default="bulk", help="Historical acquisition method")
    parser.add_argument("--refresh", action="store_true", help="Refetch historical cached pages")
    parser.add_argument("--input", type=Path, help="Use a results CSV instead of the API")
    parser.add_argument("--cache", type=Path, default=Path("data/source"))
    parser.add_argument("--output", type=Path, default=Path("data/analysis"))
    args = parser.parse_args()
    if args.input:
        frame = pd.read_csv(args.input)
    else:
        end = args.year or args.end_year or max(available_seasons())
        start = args.year or args.start_year
        if start < 1950 or start > end:
            parser.error("Require 1950 <= start year <= end year")
        loader = fetch_history if args.source == "bulk" else fetch_history_api
        frame = loader(start, end, args.cache, args.refresh)
    print(json.dumps(run(frame, args.output), indent=2))


if __name__ == "__main__":
    main()
